import streamlit as st
from profile_loader import load_uploaded_files
from chart_builder import comparison,single
from export_utils import profiles_to_zip

st.set_page_config(page_title='Cook Profile Dashboard',page_icon='🌡️',layout='wide')
st.markdown('''<style>
.stApp{background:#08111f;color:#e5edf7}[data-testid="stSidebar"]{background:#0b1727}
.kicker{color:#fb923c;font-size:.78rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase}.title{font-size:2rem;font-weight:700}.note{color:#94a3b8}
div[data-testid="stMetric"]{background:linear-gradient(145deg,#0d1b2d,#0b1929);border:1px solid #26384f;padding:1rem 1.15rem;border-radius:15px;min-height:125px}
div[data-testid="stMetricLabel"]{color:#8fa2b9;font-size:.85rem}div[data-testid="stMetricValue"]{color:#f8fafc;font-size:2rem}div[data-testid="stMetricDelta"]{color:#7f93aa}
</style>''',unsafe_allow_html=True)
if 'profiles' not in st.session_state: st.session_state.profiles=[]
P=st.session_state.profiles
with st.sidebar:
    st.header('Data')
    files=st.file_uploader('Upload CSV or Excel files',type=['csv','xlsx','xls'],accept_multiple_files=True,key='uploaded_profile_files')
    keep=st.checkbox('Keep existing profiles',True,key='keep_existing_profiles')
    if st.button('Import uploaded files',type='primary',use_container_width=True,disabled=not files,key='import_profiles_button'):
        try:
            new,msg=load_uploaded_files(files); st.session_state.profiles=(P+new) if keep else new
            for m in msg: st.info(m)
            st.success(f'Imported {len(new)} profiles'); st.rerun()
        except Exception as e: st.error(f'Import failed: {e}')
    if st.button('Clear all profiles',use_container_width=True,key='clear_profiles_button'): st.session_state.profiles=[]; st.rerun()
    st.divider(); st.header('Display')
    alignment=st.selectbox('Alignment',['Original timeline','Align peak','Align end','Clock time'],key='alignment_selector')
    theme=st.selectbox('Chart theme',['Dark','Light'],key='chart_theme_selector'); grid=st.checkbox('Grid lines',True,key='grid_lines_toggle'); legend=st.checkbox('Legend',True,key='legend_toggle'); width=st.slider('Line width',1.0,5.0,2.5,.5,key='line_width_slider')
settings={'alignment':alignment,'theme':theme,'grid':grid,'legend':legend,'width':width}
st.markdown('<div class="kicker">Cook profile studio</div><div class="title">Cook Profile Dashboard</div><div class="note">Upload, customize and compare temperature profiles. All temperatures are handled in degrees Celsius.</div>',unsafe_allow_html=True)
if not P: st.info('Upload one or more CSV or Excel files to begin.'); st.stop()
profile_by_id={p.profile_id:p for p in P}
profile_ids=list(profile_by_id)
if st.session_state.get('selected_profile_id') not in profile_by_id:
    st.session_state.selected_profile_id=profile_ids[0]
shown_ids=st.multiselect('Profiles shown',profile_ids,default=[p.profile_id for p in P if p.visible],format_func=lambda pid: profile_by_id[pid].name,key='visible_profile_ids')
visible=[profile_by_id[pid] for pid in shown_ids if pid in profile_by_id]
for p in P: p.visible=p.profile_id in shown_ids
channels=len({p.channel for p in visible}); durations=[p.duration_hours for p in visible]; mins=[p.minimum_c for p in visible]; maxs=[p.maximum_c for p in visible]
c1,c2,c3,c4=st.columns(4)
c1.metric('Visible profiles',len(visible),f'{len(P)} loaded')
c2.metric('Temperature channels',channels,'Unique channel labels')
c3.metric('Cook duration range',f'{min(durations):.1f} - {max(durations):.1f} h' if durations else 'No data','Across visible profiles')
c4.metric('Temperature range',f'{min(mins):.1f} - {max(maxs):.1f} °C' if mins else 'No data','Across visible profiles')
main,side=st.columns([3.4,1.2],gap='large')
with side:
    st.subheader('Selected profile')
    selected_id=st.selectbox('Profile',profile_ids,format_func=lambda pid: profile_by_id[pid].name,key='selected_profile_id')
    selected=profile_by_id[selected_id]
    edit_key=f'edit_{selected.profile_id}'
    new=st.text_input('Display name',selected.name,key=f'{edit_key}_name')
    channel=st.text_input('Channel label',selected.channel,key=f'{edit_key}_channel')
    offset=st.slider('Time offset (hours)',-24.0,24.0,float(selected.offset_hours),.25,key=f'{edit_key}_offset')
    color=st.color_picker('Line color',selected.color,key=f'{edit_key}_color')
    selected.channel=channel; selected.offset_hours=offset; selected.color=color
    if new!=selected.name and new:
        if any(p.name==new and p.profile_id!=selected.profile_id for p in P): st.warning('Profile names must be unique.')
        else: selected.name=new
    if st.button('Remove selected profile',use_container_width=True,key=f'remove_{selected.profile_id}'):
        remaining=[p for p in P if p.profile_id!=selected.profile_id]
        st.session_state.profiles=remaining
        st.session_state.selected_profile_id=remaining[0].profile_id if remaining else None
        st.session_state.visible_profile_ids=[p.profile_id for p in remaining if p.visible]
        st.rerun()
    st.download_button('Download visible data',profiles_to_zip(visible),'cook_profiles_export.zip','application/zip',use_container_width=True,disabled=not visible,key='download_visible_profiles')
with main:
    st.subheader('Temperature Profile Comparison')
    if visible: st.caption(f'{len(visible)} profiles | {channels} channels | {min(durations):.1f} - {max(durations):.1f} h duration range')
    st.plotly_chart(comparison(visible,settings),use_container_width=True,config={'displaylogo':False,'toImageButtonOptions':{'format':'png','filename':'cook_profiles'}})
st.divider(); st.subheader('Selected profile statistics')
a,b,c,d=st.columns(4); a.metric('Selected profile',selected.name); b.metric('Duration',f'{selected.duration_hours:.1f} h'); c.metric('Maximum temperature',f'{selected.maximum_c:.1f} °C'); d.metric('Total samples',f'{len(selected.data):,}')
st.plotly_chart(single(selected,settings),use_container_width=True,config={'displaylogo':False})
with st.expander('Preview imported data'): st.dataframe(selected.export_frame().head(500),use_container_width=True)
