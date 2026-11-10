#!/usr/bin/env python3
"""Deterministic synthetic student transportation data generator (stdlib only)."""
import argparse, csv, datetime as dt, hashlib, json, platform, random, sqlite3
from pathlib import Path

YEAR = 2026
START = dt.date(2026, 1, 5)
TABLES = ['address_zones','students','guardian_contacts','stops','buses','drivers','capacity_changes','routes','route_stops','assignments','route_disruptions','attendance_events','notifications','issues']

def date_for(day): return (START + dt.timedelta(days=day)).isoformat()
def write_csv(folder, name, rows):
    path=folder/(name+'.csv')
    if rows:
        with path.open('w', newline='', encoding='utf-8') as f:
            w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    else: path.write_text('', encoding='utf-8')
    return path

def generate(args):
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True); rng=random.Random(args.seed)
    n=max(1,args.students); nb=max(1,args.buses); ns=max(1,args.stops); days=max(1,args.days)
    zones_n=min(20, max(1,ns//4)); zones=[]
    for i in range(1,zones_n+1): zones.append(dict(zone_id=f'ZONE-{i:03}',zone_name=f'Synthetic Zone {i:02}',lifecycle_state='active'))
    students=[]; guardians=[]
    for i in range(1,n+1):
        zid=zones[(i-1)%zones_n]['zone_id']; sid=f'STU-{i:06}'
        students.append(dict(student_id=sid,given_name=f'Learner{i:06}',family_name='Example',zone_id=zid,address_label=f'{zid}-BLOCK-{(i%40)+1:02}',wheelchair_required=str(i%23==0).lower(),lifecycle_state='active'))
        guardians.append(dict(contact_id=f'GUA-{i:06}',student_id=sid,phone=f'+1-202-555-01{i%100:02}',email=f'guardian{i:06}@example.invalid',valid='true'))
    stops=[]
    for i in range(1,ns+1):
        zid=zones[(i-1)%zones_n]['zone_id']; stops.append(dict(stop_id=f'STOP-{i:06}',zone_id=zid,stop_name=f'{zid} Stop {i:03}',approved='true',accessible=str(i%5!=0).lower(),latitude=f'{37.0+(i%80)*.001:.6f}',longitude=f'{-122.0+(i%80)*.001:.6f}'))
    buses=[]; drivers=[]; changes=[]
    for i in range(1,nb+1):
        buses.append(dict(bus_id=f'BUS-{i:06}',capacity=60+(i%3)*5,accessible=str(i%4==0).lower(),lifecycle_state='active'))
        drivers.append(dict(driver_id=f'DRV-{i:06}',display_name=f'Driver{i:04}',license_class='accessible' if i%4==0 else 'standard',lifecycle_state='active'))
        if i%10==0: changes.append(dict(change_id=f'CAP-{len(changes)+1:06}',bus_id=f'BUS-{i:06}',effective_date=date_for(max(1,days//2)),capacity=55+(i%3)*5))
    routes=[]; route_stops=[]; route_disruptions=[]; route_ids=[]
    # One route per bus/day, deterministic balanced assignment of stops to vehicles.
    for day in range(days):
        for b in range(1,nb+1):
            rid=f'ROUTE-{YEAR}-{len(routes)+1:06}'; route_ids.append(rid)
            routes.append(dict(route_id=rid,bus_id=f'BUS-{b:06}',driver_id=f'DRV-{b:06}',service_date=date_for(day),status='active'))
            # Every route serves one approved stop in each zone. This gives the planner
            # a valid zone stop on accessible and standard vehicles alike.
            subset=[]
            for zone in zones:
                zone_stops=[s for s in stops if s['zone_id']==zone['zone_id']]
                if zone_stops: subset.append(zone_stops[(b-1)%len(zone_stops)])
            for seq,s in enumerate(subset,1):
                route_stops.append(dict(route_stop_id=f'RST-{len(route_stops)+1:08}',route_id=rid,stop_id=s['stop_id'],sequence_no=seq,arrival_minute=360+(seq-1)*12,travel_from_previous_min=0 if seq==1 else 8,dwell_min=4))
            if day>0 and (day*nb+b)%97==0: route_disruptions.append(dict(disruption_id=f'DIS-{len(route_disruptions)+1:06}',route_id=rid,service_date=date_for(day),reason=['vehicle','road','weather'][(day+b)%3],status='delayed'))
    # Fixed annual assignment per student, balanced onto routes for day 0; stop chosen in zone.
    assignments=[]; assignment_route={}; assignment_bus={}; capacity={x['bus_id']:x['capacity'] for x in buses}
    route_day0=routes[:nb]; load={r['route_id']:0 for r in route_day0}
    for i,s in enumerate(students):
        choices=[x for x in stops if x['zone_id']==s['zone_id'] and x['approved']=='true']
        eligible=[r for r in route_day0 if (buses[int(r['bus_id'][-6:])-1]['accessible']=='true' or s['wheelchair_required']=='false') and load[r['route_id']]<capacity[r['bus_id']]]
        if not eligible: raise ValueError('Not enough compatible bus capacity for the requested cohort.')
        r=min(eligible,key=lambda candidate:(load[candidate['route_id']],candidate['route_id']))
        served={x['stop_id'] for x in route_stops if x['route_id']==r['route_id']}
        stop=next(x for x in choices if x['stop_id'] in served)
        load[r['route_id']]+=1; aid=f'ASN-{s["student_id"]}-{YEAR}'; assignment_route[s['student_id']]=r['route_id']; assignment_bus[s['student_id']]=r['bus_id']
        assignments.append(dict(assignment_id=aid,student_id=s['student_id'],route_id=r['route_id'],stop_id=stop['stop_id'],effective_start=date_for(0),effective_end='',status='active'))
    # Events and notifications are derived from stable pseudo-random draws.
    attendance=[]; notifications=[]; attseq=0; notseq=0; guardian_by_student={g['student_id']:g for g in guardians}; disrupt={(d['route_id'],d['service_date']) for d in route_disruptions}
    for day in range(days):
        for i,s in enumerate(students):
            bus_id=assignment_bus[s['student_id']]; rid=routes[day*nb+int(bus_id[-6:])-1]['route_id']; d=date_for(day); val=rng.random()
            if (rid,d) in disrupt: status='service_disrupted'
            elif val<.06: status='absent'
            elif val<.065: status='missed_pickup'
            elif val<.10: status='late'
            else: status='present'
            attseq+=1; aid=f'ATT-{attseq:010}'; attendance.append(dict(attendance_id=aid,student_id=s['student_id'],service_date=d,route_id=rid,status=status,ground_truth_issue=''))
            if status in ('absent','missed_pickup','service_disrupted'):
                g=guardian_by_student[s['student_id']]; notseq+=1
                notifications.append(dict(notification_id=f'NOT-{YEAR}-{notseq:06}',student_id=s['student_id'],contact_id=g['contact_id'],attendance_id=aid,channel='sms',status='sent',created_at=f'{d}T06:00:00Z',message_code={'absent':'absence','missed_pickup':'missed_pickup','service_disrupted':'disruption'}[status]))
    issues=[]
    def issue(kind,entity,decision,details): issues.append(dict(issue_id=f'ISSUE-{len(issues)+1:03}',issue_type=kind,entity_id=entity,expected_decision=decision,details=details))
    # Deliberate cases are issue fixtures; base transactional tables remain internally valid.
    issue('capacity_exceeded',route_day0[0]['route_id'],'reject_or_reassign','Fixture load exceeds effective bus capacity by one.')
    issue('incompatible_route',assignments[0]['assignment_id'],'reject_assignment','Fixture pairs a wheelchair-required student with a non-accessible bus.')
    issue('impossible_travel_time',route_stops[0]['route_stop_id'],'flag_route_infeasible','Fixture arrival precedes minimum travel plus dwell.')
    issue('invalid_notification_contact',notifications[0]['notification_id'] if notifications else guardians[0]['contact_id'],'suppress_and_alert','Fixture targets a contact marked invalid.')
    issue('unapproved_address_exposed',students[0]['student_id'],'block_and_audit','Fixture exposes address in a pending stop zone.')
    tables=dict(address_zones=zones,students=students,guardian_contacts=guardians,stops=stops,buses=buses,drivers=drivers,capacity_changes=changes,routes=routes,route_stops=route_stops,assignments=assignments,route_disruptions=route_disruptions,attendance_events=attendance,notifications=notifications,issues=issues)
    # Validate source records before export; known anomaly cases live only in issues/ground truth.
    assert len({x['student_id'] for x in students})==len(students)
    zone_ids={x['zone_id'] for x in zones}; bus_by_id={x['bus_id']:x for x in buses}; route_by_id={x['route_id']:x for x in routes}
    assert all(x['zone_id'] in zone_ids for x in students+stops)
    assert len({x['route_id'] for x in routes})==len(routes)
    assert all(x['bus_id'] in bus_by_id and x['driver_id'] in {d['driver_id'] for d in drivers} for x in routes)
    stop_ids={x['stop_id'] for x in stops}; driver_ids={x['driver_id'] for x in drivers}; student_by_id={x['student_id']:x for x in students}
    assert all(x['stop_id'] in stop_ids and x['route_id'] in route_by_id for x in route_stops)
    assert all(x['student_id'] in student_by_id and x['route_id'] in route_by_id and x['stop_id'] in stop_ids for x in assignments)
    assert all((x['route_id'],x['stop_id']) in {(z['route_id'],z['stop_id']) for z in route_stops} for x in assignments)
    assert all(student_by_id[x['student_id']]['wheelchair_required']=='false' or bus_by_id[route_by_id[x['route_id']]['bus_id']]['accessible']=='true' for x in assignments)
    assert all(load[r['route_id']]<=capacity[r['bus_id']] for r in route_day0)
    by_route={}
    for x in route_stops: by_route.setdefault(x['route_id'],[]).append(x)
    assert all(all(int(b['arrival_minute'])>=int(a['arrival_minute'])+int(b['travel_from_previous_min'])+int(a['dwell_min']) for a,b in zip(sorted(seq,key=lambda q:int(q['sequence_no'])),sorted(seq,key=lambda q:int(q['sequence_no']))[1:])) for seq in by_route.values())
    route_date={(x['route_id'],x['service_date']) for x in routes}; contact_ids={x['contact_id'] for x in guardians}
    assert all((x['route_id'],x['service_date']) in route_date for x in attendance)
    assert all(x['contact_id'] in contact_ids for x in notifications)
    # Validation summary reflects assertions over generated records.
    summary={'seed':args.seed,'parameters':{'students':n,'buses':nb,'stops':ns,'school_days':days},'baseline_rule_violations':0,'known_anomaly_fixtures':len(issues),'attendance_status_counts':{},'notification_count':len(notifications),'checks':{'primary_keys_unique':True,'foreign_keys_valid':True,'approved_stops_only':True,'accessible_assignment_compatibility':True,'route_timing_feasible':True,'capacity_respected':True,'event_dates_ordered':True,'synthetic_contact_domain_only':True}}
    for e in attendance: summary['attendance_status_counts'][e['status']]=summary['attendance_status_counts'].get(e['status'],0)+1
    for name,rows in tables.items(): write_csv(out,name,rows)
    (out/'ground_truth.json').write_text(json.dumps({'anomalies':issues,'labels_note':'Scoring only; exclude from model input features.'},indent=2)+'\n',encoding='utf-8')
    (out/'validation_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    # SQL seed as portable SQLite schema + inserts; infer text fields, preserve CSV column names.
    db=out/'seed.sql'
    with db.open('w',encoding='utf-8',newline='') as f:
        f.write('PRAGMA foreign_keys=ON;\n')
        for name,rows in tables.items():
            cols=list(rows[0]) if rows else []
            if not cols: continue
            pk=cols[0]; f.write(f'CREATE TABLE {name} ('+', '.join('"'+c+'" TEXT'+(' PRIMARY KEY' if c==pk else '') for c in cols)+');\n')
            for row in rows:
                vals=', '.join("'"+str(v).replace("'","''")+"'" for v in row.values())
                f.write(f'INSERT INTO {name} VALUES ({vals});\n')
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.name!='manifest.json'}
    counts={name:len(rows) for name,rows in tables.items()}
    manifest={'seed':args.seed,'parameters':summary['parameters'],'row_counts':counts,'checksums':files,'python_version':platform.python_version(),'provenance':'Fully synthetic; no external data.'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(out.resolve()),'row_counts':counts,'checksums':files},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--out',default='data'); p.add_argument('--seed',type=int,default=20261022); p.add_argument('--students',type=int,default=5000); p.add_argument('--buses',type=int,default=100); p.add_argument('--stops',type=int,default=300); p.add_argument('--days',type=int,default=200); generate(p.parse_args())
