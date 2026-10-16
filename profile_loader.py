import csv, hashlib, io, itertools, re, uuid
from pathlib import Path
import pandas as pd
from models import CookProfile

# Line colours: 8 hues checked with a palette validator on both the light (#FFFFFF) and dark (#111827) chart
# backgrounds: distinguishable with colour-blindness, at least 3:1 contrast on both. More than 8 hues cannot be
# told apart reliably, so a 9th profile reuses the least-used colour.
COLORS=['#3987e5','#d95926','#199e70','#c98500','#d55181','#008300','#9085e9','#e66767']
TIME_WORDS=('time','date','timestamp','datetime','elapsed','hour','minute')
TEMP_WORDS=('temp','temperature','probe','meat','point','flat','pit','ambient','cavity','grate')

def _num(s):
    if pd.api.types.is_numeric_dtype(s): return pd.to_numeric(s,errors='coerce')
    x=s.astype(str).str.strip().str.replace(' ','',regex=False)
    if x.str.contains(',',regex=False).mean()>x.str.contains('.',regex=False).mean():
        x=x.str.replace('.', '',regex=False).str.replace(',','.',regex=False)
    return pd.to_numeric(x,errors='coerce')

def _to_float(text,decimal):
    text=text.strip().replace(' ','')
    if text=='': return float('nan')
    if decimal==',': text=text.replace('.','').replace(',','.')
    return float(text)

def _realign_short_rows(text):
    """Handle loggers that drop a reading when a probe disconnects.

    Some devices write fewer fields on those rows (e.g. header has 3 temperature
    columns, a row has only 2). Reading them by position can put a value in the
    wrong column. For each short row we try every way of placing the values into
    the columns (keeping their order) and choose the placement closest to each
    column's last known reading. Returns (DataFrame, short_rows, moved_rows), or
    None when the file is not ragged / cannot be handled safely.
    """
    header_line=text.lstrip('\ufeff').splitlines()[0] if text.strip() else ''
    delimiter=max(',;\t|',key=header_line.count)           # the header has no decimals, so its delimiter is unambiguous
    if header_line.count(delimiter)==0: return None
    rows=[r for r in csv.reader(io.StringIO(text),delimiter=delimiter) if any(c.strip() for c in r)]
    if len(rows)<3: return None
    header=[c.strip() for c in rows[0]]; width=len(header); body=[[c.strip() for c in r] for r in rows[1:]]
    lengths={len(r) for r in body}
    if width<3 or max(lengths)>width or lengths=={width}: return None
    decimal=',' if delimiter==';' else '.'
    last=[None]*(width-1); out=[]; short=moved=0
    try:
        for r in body:
            values=[_to_float(v,decimal) for v in r[1:]]
            slots=list(range(len(values)))                       # default: by position
            if len(values)<width-1:
                short+=1
                def cost(cols): return sum(abs(v-last[c]) for v,c in zip(values,cols) if last[c] is not None and v==v)
                best=min(itertools.combinations(range(width-1),len(values)),key=cost)
                if cost(best)<0.5*cost(tuple(slots)) and cost(tuple(slots))-cost(best)>3.0:
                    slots=list(best); moved+=1
            row=[float('nan')]*(width-1)
            for v,c in zip(values,slots):
                row[c]=v
                if v==v: last[c]=v
            out.append([r[0]]+row)
    except ValueError:
        return None
    return pd.DataFrame(out,columns=header),short,moved

# ---- Time column -------------------------------------------------------------------------------------------
TIME_HEADER=re.compile(r'time|date|elapsed|hour|minute|second|\bzeit\b|\bdatum\b|\btid\b|\bdato\b',re.I)
ZONE_HOURS={'UTC':0,'GMT':0,'Z':0,'WET':0,'WEST':1,'BST':1,'CET':1,'CEST':2,'EET':2,'EEST':3,'MSK':3,
            'EST':-5,'EDT':-4,'CDT':-5,'MST':-7,'MDT':-6,'PST':-8,'PDT':-7}
ZONE_NAME=re.compile(r'(?<=\d)\s+([A-Z]{3,5})\s*$')                                  # 15:49:31 CEST (AM/PM untouched)
ZONE_OFFSET=re.compile(r'(\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?)\s*(?:UTC|GMT)?\s*([+-])(\d{1,2})(?::?(\d{2}))?\s*$')  # 15:49:31+02:00 (a time must come first)
ZONE_Z=re.compile(r'(?<=\d)Z\s*$')                                                    # 13:49:31Z
ISO_DATE=re.compile(r'^\s*\d{4}-\d{1,2}-\d{1,2}')
DAY_FIRST_FORMATS=('%d/%m/%Y %H:%M:%S','%d/%m/%Y %H:%M','%d.%m.%Y %H:%M:%S','%d.%m.%Y %H:%M','%d-%m-%Y %H:%M:%S','%d-%m-%Y %H:%M',
                   '%d/%m/%Y %H:%M:%S.%f','%d.%m.%Y %H:%M:%S.%f','%d/%m/%Y','%d.%m.%Y')

def _zone_hours(text):
    """Split a trailing time-zone (name, offset or Z) off each text; return (text without it, offset in hours or NaN)."""
    text=text.astype('string').str.strip()
    hours=pd.Series(float('nan'),index=text.index)
    m=text.str.extract(ZONE_OFFSET)
    has=m[1].notna()
    if has.any():
        sign=m.loc[has,1].map({'+':1,'-':-1}).astype(float)
        hours[has]=sign*(m.loc[has,2].astype(float)+m.loc[has,3].fillna('0').astype(float)/60)
        text[has]=text[has].str.replace(ZONE_OFFSET,r'\1',regex=True)                   # keep the time, drop the offset
    z=text.str.contains(ZONE_Z,na=False)
    if z.any():
        hours[z]=0.0; text[z]=text[z].str.replace(ZONE_Z,'',regex=True)
    name=text.str.extract(ZONE_NAME)[0]
    known=name.isin(list(ZONE_HOURS))&hours.isna()
    if known.any():
        hours[known]=name[known].map(ZONE_HOURS).astype(float)
    unknown=name.notna()&~name.isin(list(ZONE_HOURS))
    text[known|unknown]=text[known|unknown].str.replace(ZONE_NAME,'',regex=True)   # unknown names are dropped, as before
    return text.str.strip(),hours

def _parse_text_times(text):
    """Year-first text as year-month-day; anything else as day-month-year (never the other way round)."""
    out=pd.Series(pd.NaT,index=text.index,dtype='datetime64[ns]')
    iso=text.str.match(ISO_DATE,na=False)
    if iso.any():
        out[iso]=pd.to_datetime(text[iso].str.replace('T',' ',regex=False),format='ISO8601',errors='coerce')
    rest=~iso&text.notna()
    if rest.any():
        sample=text[rest]
        for fmt in DAY_FIRST_FORMATS:                       # a fixed format is fast and never guesses month/day
            parsed=pd.to_datetime(sample,format=fmt,errors='coerce')
            if parsed.notna().mean()>=.9:
                out[rest]=parsed; break
        else:
            out[rest]=pd.to_datetime(sample,errors='coerce',dayfirst=True)
    return out

def _one_continuous_clock(times,hours,zone_labels):
    """Readings that carry a zone are put on the clock in force at the first reading, so a clock change
    (CEST to CET) neither reorders readings nor adds or removes an hour. Without zones, a single backward
    jump of about an hour in an otherwise forward-running log is treated as the autumn clock change."""
    note=''
    if hours.notna().any():
        hours=hours.ffill().bfill()
        first=float(hours[times.notna()].iloc[0]) if times.notna().any() else float(hours.iloc[0])
        times=times-pd.to_timedelta(hours,unit='h')+pd.Timedelta(first,unit='h')
        if hours.nunique()>1:
            names=[z for z in dict.fromkeys(zone_labels.dropna()) if z]
            change=' to '.join(names[:2]) if len(names)>=2 else 'a different UTC offset'
            note=(f'the clock changed during this cook ({change}); all times are shown on one continuous clock, '
                  f'{names[0] if names else f"UTC{first:+g}"} as at the start.')
        return times,note
    valid=times.dropna()
    if len(valid)>=3:
        steps=valid.diff().dt.total_seconds().div(60).iloc[1:]
        typical=steps[steps>0].median() if (steps>0).any() else None
        # the wall clock steps back by one hour minus the time between readings
        back=steps[(steps<0)&(steps>=-62)&(steps<=-(60-3*(typical or 0)-2))] if typical is not None else steps.iloc[0:0]
        if len(back)==1 and typical<=30 and (steps<0).sum()==1:
            after=times.index>=back.index[0]
            times=times.copy(); times[after]=times[after]+pd.Timedelta(1,unit='h')
            note=('the time went back by about an hour during this cook, as when the clocks change in autumn; '
                  'later readings are shown one hour on, so the cook stays on one continuous clock.')
    return times,note

def parse_clock(values,header=''):
    """Clock times from a column as naive datetimes on one continuous clock, with a note; None if not clock times."""
    if pd.api.types.is_datetime64_any_dtype(values):
        times=values
        if getattr(times.dt,'tz',None) is not None:
            local=times.dt.tz_localize(None); utc=times.dt.tz_convert('UTC').dt.tz_localize(None)
            hours=(local-utc).dt.total_seconds()/3600
            return _one_continuous_clock(local,hours,pd.Series(dtype='string'))
        return _one_continuous_clock(times,pd.Series(float('nan'),index=times.index),pd.Series(dtype='string'))
    if pd.api.types.is_numeric_dtype(values):
        # Numbers are elapsed time, except Excel date serial numbers under a date/time header (e.g. 46298.5)
        n=pd.to_numeric(values,errors='coerce').dropna()
        if TIME_HEADER.search(header) and len(n) and n.min()>=20000 and n.max()<=100000 and n.max()-n.min()<60:
            return pd.to_datetime(pd.to_numeric(values,errors='coerce'),unit='D',origin='1899-12-30').dt.round('ms'),''
        return None
    text,hours=_zone_hours(values)
    zone_labels=values.astype('string').str.strip().str.extract(r'([A-Z]{2,5}|[+-]\d{1,2}:?\d{2})\s*$')[0]
    times=_parse_text_times(text)
    return _one_continuous_clock(times,hours,zone_labels)

def _elapsed_hours(values,label):
    n=_num(values)
    if 'minute' in label or re.search(r'\bmins?\b',label): n=n/60
    elif 'second' in label or re.search(r'\bsecs?\b|\(s\)',label): n=n/3600
    return n

def _time(df):
    """Find the time column: clock times first, then elapsed time; columns with a time-like header are tried first."""
    named=[c for c in df if TIME_HEADER.search(str(c))]
    for c in named+[c for c in df if c not in named]:
        parsed=parse_clock(df[c],str(c))
        if parsed is None: continue
        times,note=parsed
        if times.notna().mean()>=.75 and times.nunique()>1:
            base=times.dropna().min()
            return (times-base).dt.total_seconds()/3600,times,str(c),note
    for c in named:                                        # elapsed time, only from a column whose header says so
        n=_elapsed_hours(df[c],str(c).lower())
        if n.notna().mean()>=.75 and n.nunique()>1:
            return n-n.dropna().min(),None,str(c),''
    return pd.Series(range(len(df)),index=df.index,dtype=float),None,'row number',''

# ---- Temperature columns -----------------------------------------------------------------------------------
SETPOINT_WORDS=('set','target','setpoint','soll')
NOT_TEMPERATURE=re.compile(r'%|\bfan\b|battery|\bbatt\b|humid|\brpm\b|signal|rssi|volt|\bid\b|status|alarm|power|speed|damper|blower',re.I)
CELSIUS=re.compile(r'\s*[\(\[]\s*(?:°\s*C|deg\s*C|celsius)\s*[\)\]]\s*$|\s+°\s*C\s*$',re.I)
FAHRENHEIT=re.compile(r'\s*[\(\[]?\s*(?:°\s*F|deg\s*F|fahrenheit)\s*[\)\]]?|\s*[\(\[]\s*F\s*[\)\]]',re.I)

def _temperature_columns(df,timecol):
    """Every column that holds temperatures. Returns [(column, display name, values in °C, note)] and [(column, reason)]."""
    keep,skipped=[],[]
    for c in df:
        if str(c)==timecol: continue
        label=str(c); lower=label.lower()
        if TIME_HEADER.search(label) and not any(w in lower for w in TEMP_WORDS):
            skipped.append((label,'a time column')); continue
        if NOT_TEMPERATURE.search(label):
            skipped.append((label,'not a temperature')); continue
        raw=df[c]; filled=raw.notna()&(raw.astype('string').str.strip()!='')
        n=_num(raw); values=n.dropna()
        if len(values)<2 or len(values)<0.9*filled.sum():          # text, notes or mostly empty
            skipped.append((label,'no temperature readings')); continue
        note=''; name=label
        if CELSIUS.search(label): name=CELSIUS.sub('',label).strip() or label
        if FAHRENHEIT.search(label):
            n=(n-32)*5/9; values=n.dropna(); name=FAHRENHEIT.sub('',label).strip() or label
            note=f'"{label}" was in °F and has been converted to °C.'
        if values.between(-50,400).mean()<.9:
            skipped.append((label,'values outside the temperature range')); continue
        if values.nunique()<2 and not any(w in lower for w in TEMP_WORDS+SETPOINT_WORDS):
            skipped.append((label,'the same value throughout')); continue
        keep.append((c,name,n,note))
    return keep,skipped

START_SOURCE=re.compile(r'^start\s*time\s*(source|set|set\s*by)$',re.I)

def _start_source(df):
    """BBQ Chart to Data writes how each probe's start time was set ("read and confirmed" from a start
    screenshot, or "typed") into a text column "Start time source". Returns (value or '', df without it)."""
    for c in df.columns:
        if START_SOURCE.match(str(c).strip()):
            values=df[c].dropna().astype(str).str.strip()
            values=values[values!='']
            return (values.mode().iloc[0] if len(values) else ''), df.drop(columns=[c])
    return '', df

def dataframe_to_profiles(df,source,sheet=None,color_start=0):
    df=df.rename(columns=lambda c: str(c).strip()).dropna(how='all').dropna(axis=1,how='all')
    start_source,df=_start_source(df)
    elapsed,timestamp,timecol,clock_note=_time(df)
    columns,skipped=_temperature_columns(df,timecol)
    profiles=[]; notes=[]
    for i,(c,name,values,note) in enumerate(columns):
        out=pd.DataFrame({'elapsed_hours':elapsed,'temperature_c':values})
        if timestamp is not None: out['timestamp']=timestamp
        out=out.dropna(subset=['elapsed_hours','temperature_c']).sort_values('elapsed_hours').drop_duplicates('elapsed_hours',keep='last')
        if len(out)<2: continue
        base=Path(source).stem; full=f'{base} - {sheet} - {name}' if sheet else f'{base} - {name}'
        profiles.append(CookProfile(uuid.uuid4().hex,full,source,name,COLORS[(color_start+i)%len(COLORS)],out.reset_index(drop=True),
                                    metadata={'sheet':sheet or '', 'time_column':timecol, 'start_source':start_source}))
        if note: notes.append(note)
    where=f'{source} ({sheet})' if sheet else source
    message=f"{where}: detected '{timecol}' and created {len(profiles)} profile(s)."
    if clock_note: message+=' Note: '+clock_note
    if start_source and 'typed' in start_source.lower():
        message+=' Start time typed in Chart to Data, not read from a start screenshot: check it.'
    elif start_source:
        message+=f' Start time: {start_source}.'
    for note in notes: message+=' '+note
    if skipped: message+=' Skipped: '+'; '.join(f'"{c}" ({why})' for c,why in skipped)+'.'
    return profiles,message

def _read_csv(raw,name):
    text=None
    for encoding in ('utf-8-sig','utf-8','latin-1'):
        try: text=raw.decode(encoding); break
        except UnicodeDecodeError: pass
    note=''
    ragged=_realign_short_rows(text)
    if ragged is not None:
        table,short,moved=ragged
        note=f"{name}: {short} row(s) had fewer values than the header (probe dropouts)"+(f"; {moved} were re-assigned to the matching probe column." if moved else "; none needed re-assigning.")
        return table,note
    for encoding in ('utf-8-sig','utf-8','latin-1'):
        try: return pd.read_csv(io.BytesIO(raw),encoding=encoding,sep=None,engine='python'),note
        except Exception: pass
    raise ValueError('the file could not be parsed as CSV')

def file_fingerprint(raw):
    """Identifies a file by its content, so the same file is not imported twice."""
    return hashlib.sha1(raw).hexdigest()

def assign_colours(new,existing):
    """Give each new profile the first colour not yet in use; past 8 profiles, the least-used colour."""
    counts={c:0 for c in COLORS}
    for p in existing:
        if p.color in counts: counts[p.color]+=1
    for p in new:
        colour=min(COLORS,key=lambda c:(counts[c],COLORS.index(c)))
        p.color=colour; counts[colour]+=1
    return new

def load_uploaded_files(files,existing=None):
    """Profiles from uploaded files. Files whose content is already loaded (in `existing` or earlier in this
    batch) are skipped with a note; new profiles get colours that are not in use yet."""
    existing=list(existing or [])
    seen={p.metadata.get('fingerprint') for p in existing}
    result=[]; messages=[]
    for f in files:
        try:
            raw=f.getvalue(); ext=Path(f.name).suffix.lower()
            fingerprint=file_fingerprint(raw)
            if fingerprint in seen:
                messages.append(f'{f.name}: already imported, skipped.'); continue
            seen.add(fingerprint)
            if ext=='.csv':
                table,note=_read_csv(raw,f.name); tables={None:table}
                if note: messages.append(note)
            else:
                tables=pd.read_excel(io.BytesIO(raw),sheet_name=None,engine='xlrd' if ext=='.xls' else 'openpyxl')
                if len(tables)==1: tables={None:next(iter(tables.values()))}   # one sheet: no sheet name in profile names
            for sheet,df in tables.items():
                p,m=dataframe_to_profiles(df,f.name,sheet,0)
                for profile in p: profile.metadata['fingerprint']=fingerprint
                result.extend(p); messages.append(m)
        except Exception as exc:
            messages.append(f'{f.name}: skipped, {exc}')
    assign_colours(result,existing)
    return result,messages
