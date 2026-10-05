import csv, io, itertools, re, uuid
from pathlib import Path
import pandas as pd
from models import CookProfile

COLORS=['#f97316','#38bdf8','#a78bfa','#22c55e','#f43f5e','#eab308','#14b8a6','#fb7185']
TIME_WORDS=('time','date','timestamp','datetime','elapsed','hour','minute')
TEMP_WORDS=('temp','temperature','probe','meat','point','flat','pit','ambient','cavity','grate')

def _num(s):
    if pd.api.types.is_numeric_dtype(s): return pd.to_numeric(s,errors='coerce')
    x=s.astype(str).str.strip().str.replace(' ','',regex=False)
    if x.str.contains(',',regex=False).mean()>x.str.contains('.',regex=False).mean():
        x=x.str.replace('.', '',regex=False).str.replace(',','.',regex=False)
    return pd.to_numeric(x,errors='coerce')

TZ_SUFFIX=re.compile(r'\s+(?:[A-Z]{3,5}|(?:UTC|GMT)\s*[+-]?\d{0,2}(?::?\d{2})?)\s*$')

def _strip_timezone(s):
    """Remove trailing zone names such as CEST/UTC/GMT+2 that pandas cannot parse."""
    if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s): return s
    return s.astype(str).str.strip().str.replace(TZ_SUFFIX,'',regex=True)

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

def _time(df):
    labels={c:str(c).lower() for c in df.columns}
    order=[c for c in df if any(w in labels[c] for w in TIME_WORDS)]+[c for c in df if not any(w in labels[c] for w in TIME_WORDS)]
    for c in order:
        p=pd.to_datetime(_strip_timezone(df[c]),errors='coerce',dayfirst=True)
        if p.notna().mean()>=.75 and p.nunique()>1:
            return (p-p.dropna().iloc[0]).dt.total_seconds()/3600,p,str(c)
    for c in order:
        n=_num(df[c])
        if n.notna().mean()>=.75 and n.nunique()>1:
            label=labels[c]
            if 'minute' in label or re.search(r'\bmin\b',label): n=n/60
            if 'second' in label or re.search(r'\bsec\b',label): n=n/3600
            return n-n.dropna().iloc[0],None,str(c)
    return pd.Series(range(len(df)),index=df.index,dtype=float),None,'row number'

def dataframe_to_profiles(df,source,sheet=None,color_start=0):
    df=df.rename(columns=lambda c: str(c).strip()).dropna(how='all').dropna(axis=1,how='all')
    elapsed,timestamp,timecol=_time(df)
    columns=[]
    for c in df:
        if str(c)==timecol: continue
        n=_num(df[c]); label=str(c).lower()
        if n.notna().mean()>=.6 and n.nunique()>1 and n.dropna().between(-50,400).mean()>=.9:
            columns.append((2 if any(w in label for w in TEMP_WORDS) else 0,str(c)))
    preferred=[c for score,c in columns if score]
    columns=preferred or [c for _,c in columns]
    profiles=[]
    for i,c in enumerate(columns):
        out=pd.DataFrame({'elapsed_hours':elapsed,'temperature_c':_num(df[c])})
        if timestamp is not None: out['timestamp']=timestamp
        out=out.dropna(subset=['elapsed_hours','temperature_c']).sort_values('elapsed_hours').drop_duplicates('elapsed_hours',keep='last')
        if len(out)<2: continue
        base=Path(source).stem; name=f'{base} - {sheet} - {c}' if sheet else f'{base} - {c}'
        profiles.append(CookProfile(uuid.uuid4().hex,name,source,str(c),COLORS[(color_start+i)%len(COLORS)],out.reset_index(drop=True),metadata={'sheet':sheet or '', 'time_column':timecol}))
    return profiles,f"{source}: detected '{timecol}' and created {len(profiles)} profile(s)."

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

def load_uploaded_files(files):
    result=[]; messages=[]
    for f in files:
        try:
            raw=f.getvalue(); ext=Path(f.name).suffix.lower()
            if ext=='.csv':
                table,note=_read_csv(raw,f.name); tables={None:table}
                if note: messages.append(note)
            else:
                tables=pd.read_excel(io.BytesIO(raw),sheet_name=None,engine='xlrd' if ext=='.xls' else 'openpyxl')
            for sheet,df in tables.items():
                p,m=dataframe_to_profiles(df,f.name,sheet,len(result)); result.extend(p); messages.append(m)
        except Exception as exc:
            messages.append(f'{f.name}: skipped, {exc}')
    return result,messages
