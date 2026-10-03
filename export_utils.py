import io,re,zipfile
def profiles_to_zip(profiles):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        for p in profiles:
            name=re.sub(r'[^A-Za-z0-9._-]+','_',p.name).strip('_') or 'profile'
            z.writestr(name+'.csv',p.export_frame().to_csv(index=False))
    return b.getvalue()
