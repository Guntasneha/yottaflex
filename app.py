"""School transportation assignment and safety operations demo."""
from pathlib import Path
import subprocess, sys
from html import escape
import pandas as pd
import streamlit as st

st.set_page_config(page_title="RouteWise | School Transport", page_icon="🚌", layout="wide")
ROOT = Path(__file__).parent
DATA = ROOT / "demo_data"

@st.cache_data
def load_data(folder: str):
    p = Path(folder)
    names = ['students','guardian_contacts','stops','buses','routes','route_stops','assignments','attendance_events','notifications','issues','capacity_changes','route_disruptions']
    return {n: pd.read_csv(p/f'{n}.csv', keep_default_na=False) for n in names}

def ensure_demo():
    if not (DATA/'students.csv').exists():
        subprocess.run([sys.executable, str(ROOT/'generate.py'), '--out', str(DATA), '--students','120','--buses','12','--stops','36','--days','20','--seed','20261022'], check=True)

def render_bars(frame, label_col, value_col, title, suffix=''):
    """Draw a small HTML chart without importing Altair or network-backed datasets."""
    if frame.empty:
        st.info('No data for this selection.')
        return
    maximum=max(float(frame[value_col].max()),1.0)
    palette=['#1d7a68','#52a58d','#8ac6ad','#d58b42','#cb5d52','#6684b7']
    rows=[]
    for i, row in frame.reset_index(drop=True).iterrows():
        label=escape(str(row[label_col]))
        value=float(row[value_col])
        width=max(2.0,100.0*value/maximum)
        rows.append(f"<div class='rw-row'><span class='rw-label'>{label}</span><span class='rw-track'><span class='rw-fill' style='width:{width:.2f}%;background:{palette[i%len(palette)]}'></span></span><span class='rw-value'>{value:g}{escape(suffix)}</span></div>")
    html=f"<section class='rw-chart'><div class='rw-title'>{escape(title)}</div>{''.join(rows)}</section>"
    st.markdown("<style>.rw-chart{padding:12px 0}.rw-title{font-size:1rem;font-weight:600;margin-bottom:14px}.rw-row{display:grid;grid-template-columns:minmax(90px,145px) 1fr 54px;align-items:center;gap:10px;margin:10px 0}.rw-label{font-size:.86rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.rw-track{height:12px;background:#e9efec;border-radius:8px;overflow:hidden}.rw-fill{display:block;height:100%;border-radius:8px}.rw-value{font-size:.84rem;text-align:right;color:#40534d}</style>"+html,unsafe_allow_html=True)

ensure_demo()
db = load_data(str(DATA))
students, buses, assignments, attendance = db['students'], db['buses'], db['assignments'], db['attendance_events']

st.title("RouteWise")
st.caption("School transportation planning · synthetic operations workspace")
with st.sidebar:
    st.header("Workspace")
    page = st.radio("Open", ["Operations overview", "Assignment planner", "Attendance & alerts", "Exception review", "Data explorer"])
    st.divider()
    st.caption("Demo records are synthetic. Guardian details use fictional reserved domains and numbers.")

if page == "Operations overview":
    st.subheader("Today’s service picture")
    date = st.selectbox("Service date", sorted(attendance.service_date.unique()))
    today = attendance[attendance.service_date == date]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Students", f"{len(students):,}")
    c2.metric("Active assignments", f"{len(assignments):,}")
    c3.metric("Present", f"{(today.status == 'present').sum():,}")
    c4.metric("Needs follow-up", f"{today.status.isin(['absent','missed_pickup','service_disrupted']).sum():,}")
    left,right=st.columns([1.4,1])
    with left:
        counts=today.status.value_counts().rename_axis('Status').reset_index(name='Students')
        render_bars(counts,'Status','Students','Attendance outcomes')
    with right:
        load=assignments.merge(db['routes'][['route_id','bus_id']],on='route_id').groupby('bus_id').size().rename('Assigned').reset_index().merge(buses[['bus_id','capacity']],on='bus_id')
        load['Utilization %']=(100*load.Assigned/load.capacity).round(1)
        render_bars(load,'bus_id','Utilization %','Seat utilization by bus','%')
    st.subheader("Service exceptions")
    st.dataframe(db['issues'][['issue_type','entity_id','expected_decision','details']],hide_index=True,use_container_width=True)

elif page == "Assignment planner":
    st.subheader("Find a safe route assignment")
    st.write("The planner filters to approved stops in the student’s zone, checks accessibility, then checks route capacity.")
    student_id=st.selectbox("Student",students.student_id.tolist(),format_func=lambda x: f"{x} · {students.loc[students.student_id.eq(x),'given_name'].iloc[0]} {students.loc[students.student_id.eq(x),'family_name'].iloc[0]}")
    s=students.loc[students.student_id.eq(student_id)].iloc[0]
    already=assignments.loc[assignments.student_id.eq(student_id)].iloc[0]
    zone_stops=db['stops'][(db['stops'].zone_id==s.zone_id)&(db['stops'].approved.astype(str).str.lower()=='true')]
    routes=db['routes'].drop_duplicates('route_id').merge(buses,on='bus_id').merge(db['route_stops'].groupby('route_id').stop_id.apply(list).rename('stop_ids'),on='route_id')
    routes=routes[(routes.status.isin(['active','planned'])) & ((s.wheelchair_required=='false') | (routes.accessible.astype(str).str.lower()=='true'))]
    load=assignments.merge(db['routes'][['route_id','bus_id']],on='route_id').groupby('route_id').size()
    routes['assigned']=routes.route_id.map(load).fillna(0).astype(int)
    routes['remaining']=routes.capacity.astype(int)-routes.assigned
    candidates=[]
    for _,stop in zone_stops.iterrows():
        for _,r in routes.iterrows():
            if stop.stop_id in r.stop_ids and r.remaining>0:
                candidates.append({'stop_id':stop.stop_id,'stop_name':stop.stop_name,'route_id':r.route_id,'bus_id':r.bus_id,'seats_left':int(r.remaining),'accessible':r.accessible})
    st.info(f"Student zone: {s.zone_id} · Accessible vehicle required: {'Yes' if s.wheelchair_required=='true' else 'No'}")
    if candidates:
        options=pd.DataFrame(candidates)
        st.success(f"{len(options)} safe candidate combinations found. Current assignment: {already.route_id} at {already.stop_id}.")
        st.dataframe(options,hide_index=True,use_container_width=True)
    else:
        st.error("No feasible route found. Escalate for capacity planning or accessible service review; do not assign an incompatible route.")
    st.caption("This demo displays candidate decisions. Assignment changes are not persisted to the source dataset.")

elif page == "Attendance & alerts":
    st.subheader("Daily attendance and guardian notifications")
    date=st.selectbox("Service date", sorted(attendance.service_date.unique()))
    day=attendance[attendance.service_date==date].merge(students[['student_id','given_name','family_name','zone_id']],on='student_id')
    st.dataframe(day[['student_id','given_name','family_name','zone_id','route_id','status']],hide_index=True,use_container_width=True)
    alerts=day[day.status.isin(['absent','missed_pickup','service_disrupted'])]
    st.markdown("#### Follow-up queue")
    joined=alerts.merge(db['notifications'][['attendance_id','status','channel','message_code']],left_on='attendance_id',right_on='attendance_id',how='left')
    st.dataframe(joined[['student_id','status_x','message_code','channel']],hide_index=True,use_container_width=True)
    st.caption("Notifications are derived from attendance events. Only synthetic contact identifiers and message codes are stored.")

elif page == "Exception review":
    st.subheader("Known scenario review")
    st.warning("These labeled scenarios are scoring fixtures. They are separate from normal operational records and must stay out of model input features.")
    issues=db['issues']
    selected=st.selectbox("Scenario",issues.issue_type.tolist())
    issue=issues[issues.issue_type==selected].iloc[0]
    st.markdown(f"**Issue:** `{issue.issue_type}`  \n**Entity:** `{issue.entity_id}`  \n**Expected action:** {issue.expected_decision}  \n**Fixture detail:** {issue.details}")
    st.markdown("#### Decision policy")
    st.write({
        'capacity_exceeded':'Reject or reassign before publishing the run sheet.',
        'incompatible_route':'Block the assignment and find an accessible vehicle.',
        'impossible_travel_time':'Mark the route infeasible and recompute its sequence.',
        'invalid_notification_contact':'Suppress delivery and create a support follow-up.',
        'unapproved_address_exposed':'Block exposure and retain an audit event.'
    }.get(selected,'Review against the documented policy.'))

else:
    st.subheader("Generated data tables")
    key=st.selectbox("Table",list(db.keys()))
    st.caption(f"{len(db[key]):,} rows")
    st.dataframe(db[key],use_container_width=True,height=550)
    st.download_button("Download this table as CSV",db[key].to_csv(index=False).encode(),file_name=f'{key}.csv',mime='text/csv')
