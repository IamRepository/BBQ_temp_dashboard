import io, re, zipfile


def profiles_to_zip(profiles):
    b = io.BytesIO()
    used = {}
    with zipfile.ZipFile(b, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in profiles:
            name = re.sub(r'[^A-Za-z0-9._-]+', '_', p.name).strip('_') or 'profile'
            used[name] = used.get(name, 0) + 1
            if used[name] > 1:
                name = f'{name}_{used[name]}'  # never let two profiles overwrite each other in the zip
            z.writestr(name + '.csv', p.export_frame().to_csv(index=False))
    return b.getvalue()
