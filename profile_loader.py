import io, re, uuid
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

def _time(df):
    labels={c:str(c).lower() for c in df.columns}
    order=[c for c in df if any(w in labels[c] for w in TIME_WORDS)]+[c for c in df if not any(w in labels[c] for w in TIME_WORDS)]
    for c in order:
        p=pd.to_datetime(df[c],errors='coerce',dayfirst=True)
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
    df=df.dropna(how='all').dropna(axis=1,how='all')
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

def load_uploaded_files(files):
    result=[]; messages=[]
    for f in files:
        raw=f.getvalue(); ext=Path(f.name).suffix.lower()
        if ext=='.csv':
            table=None
            for encoding in ('utf-8-sig','utf-8','latin-1'):
                try: table=pd.read_csv(io.BytesIO(raw),encoding=encoding,sep=None,engine='python'); break
                except Exception: pass
            tables={None:table}
        else:
            tables=pd.read_excel(io.BytesIO(raw),sheet_name=None,engine='xlrd' if ext=='.xls' else 'openpyxl')
        for sheet,df in tables.items():
            p,m=dataframe_to_profiles(df,f.name,sheet,len(result)); result.extend(p); messages.append(m)
    return result,messages
