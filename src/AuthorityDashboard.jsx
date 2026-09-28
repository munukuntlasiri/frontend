import { useState } from "react";

const initialIssues = [
  {
    id: "MI-2026-0041",
    title: "Large pothole on main road",
    category: "Road damage",
    priority: "High",
    reports: 23,
    status: "In progress",
    department: "Road Maintenance",
    location: "Main residential road",
    updated: "12 min ago",
  },
  {
    id: "MI-2026-0038",
    title: "Overflowing waste collection point",
    category: "Waste",
    priority: "Medium",
    reports: 7,
    status: "New",
    department: "Sanitation",
    location: "Community market area",
    updated: "34 min ago",
  },
  {
    id: "MI-2026-0034",
    title: "Low water pressure reported",
    category: "Water",
    priority: "Medium",
    reports: 3,
    status: "Assigned",
    department: "Water Supply",
    location: "North residential block",
    updated: "1 hr ago",
  },
];

const activity = [
  ["10:42 AM", "Master issue updated", "23 citizen reports are now grouped under MI-2026-0041."],
  ["10:18 AM", "Repair work started", "Road Maintenance marked the pothole issue as in progress."],
  ["9:54 AM", "Issue assigned", "MI-2026-0034 was assigned to Water Supply."],
  ["9:31 AM", "New civic report", "A waste collection issue was reported near the community market."],
];

const categoryData = [
  ["Road damage", 42],
  ["Waste", 31],
  ["Water", 18],
  ["Streetlights", 12],
  ["Other", 5],
];

function slug(value) {
  return String(value).toLowerCase().replace(/\s+/g, "-");
}

function AuthorityHeader({ onBack }) {
  return (
    <header className="authority-topbar">
      <div className="authority-brand-lockup">
        <div className="authority-brand-mark">CR</div>
        <div>
          <strong>CivicResolve</strong>
          <span>Authority Portal</span>
        </div>
      </div>

      <div className="authority-user">
        <div>
          <strong>Road Maintenance</strong>
          <span>Official workspace</span>
        </div>
        <div className="authority-avatar">RM</div>
        <button className="authority-logout" onClick={onBack}>Exit</button>
      </div>
    </header>
  );
}

function IssueMap({ issues, onSelect, large = false }) {
  return (
    <div className={`authority-map impact-map${large ? " large-map" : ""}`}>
      <div className="map-grid-lines" />
      <div className="map-road road-one" />
      <div className="map-road road-two" />
      <div className="map-road road-three" />
      <div className="map-road road-four" />

      <div className="map-area-label area-north">NORTH RESIDENTIAL</div>
      <div className="map-area-label area-market">COMMUNITY MARKET</div>
      <div className="map-area-label area-main">MAIN ROAD CORRIDOR</div>
      <div className="map-area-label area-east">EAST SERVICE AREA</div>
      <div className="map-north-indicator" aria-hidden="true">N</div>

      <button className="map-marker marker-one" onClick={() => onSelect(issues[0].id)} aria-label="Open pothole issue">
        <span>{issues[0].reports}</span>
      </button>
      <button className="map-marker marker-two" onClick={() => onSelect(issues[1].id)} aria-label="Open waste issue">
        <span>{issues[1].reports}</span>
      </button>
      <button className="map-marker marker-three" onClick={() => onSelect(issues[2].id)} aria-label="Open water issue">
        <span>{issues[2].reports}</span>
      </button>

      <div className="map-legend">
        <span><i className="legend-red" />High</span>
        <span><i className="legend-amber" />Medium</span>
        <span><i className="legend-green" />Resolved</span>
      </div>
      <span className="map-label">Approximate locations shown for demonstration</span>
    </div>
  );
}

function IssueDetail({ issue, issues, setIssues, onBack, showToast }) {
  const updateStatus = (status, message) => {
    setIssues((current) =>
      current.map((item) =>
        item.id === issue.id ? { ...item, status, updated: "just now" } : item
      )
    );
    showToast(message);
  };

  return (
    <main className="authority-page authority-detail-page">
      <AuthorityHeader onBack={onBack} />
      <div className="authority-shell">
        <button className="authority-text-back" onClick={onBack}>← Back to dashboard</button>

        <div className="authority-detail-heading">
          <div>
            <p className="eyebrow">MASTER CIVIC ISSUE · {issue.id}</p>
            <h1>{issue.title}</h1>
            <p>{issue.location} · {issue.department}</p>
          </div>
          <span className={`authority-status ${slug(issue.status)}`}>{issue.status}</span>
        </div>

        <section className="authority-detail-hero">
          <div className="authority-detail-stat"><span>Citizen reports</span><strong>{issue.reports}</strong><small>Grouped reports</small></div>
          <div className="authority-detail-stat"><span>Priority</span><strong>{issue.priority}</strong><small>Community signal</small></div>
          <div className="authority-detail-stat"><span>Department</span><strong>{issue.department}</strong><small>Responsible team</small></div>
          <div className="authority-detail-stat"><span>Updated</span><strong>{issue.updated}</strong><small>Latest activity</small></div>
        </section>

        <section className="authority-detail-grid">
          <div className="authority-main-column">
            <section className="authority-panel authority-feature-panel">
              <div className="panel-heading-row">
                <div><p className="eyebrow">ISSUE INTELLIGENCE</p><h2>What the system understands</h2></div>
                <span className="authority-ai-badge">AI assisted</span>
              </div>
              <p className="authority-large-copy">
                Multiple citizen reports describe a civic problem at approximately the same location. CivicResolve groups related reports into one Master Civic Issue so the responsible department can coordinate a single response.
              </p>
              <div className="authority-insight-row">
                <div><strong>Community signal</strong><span>{issue.reports} citizen reports linked to this issue.</span></div>
                <div><strong>Routing</strong><span>Assigned to {issue.department}.</span></div>
              </div>
            </section>

            <section className="authority-panel">
              <div className="panel-heading-row">
                <div><p className="eyebrow">RESOLUTION WORKFLOW</p><h2>Move this issue forward</h2></div>
                <span className="workflow-note">Authority action</span>
              </div>
              <div className="authority-actions-grid">
                <button className="authority-action-button" onClick={() => updateStatus("Acknowledged", "Issue acknowledged")}>Acknowledge</button>
                <button className="authority-action-button" onClick={() => updateStatus("Assigned", "Issue assigned to the department")}>Assign</button>
                <button className="authority-action-button primary" onClick={() => updateStatus("In progress", "Repair work marked as in progress")}>Start Work</button>
                <button className="authority-action-button" onClick={() => showToast("Evidence request sent to the field team")}>Request Evidence</button>
                <button className="authority-action-button" onClick={() => updateStatus("Ready for verification", "Issue is ready for resolution verification")}>Ready for Verification</button>
              </div>
              <div className="followup-row">
                <div><strong>Follow-up monitoring active</strong><span>Automatic reminders can be triggered when an issue remains unresolved.</span></div>
                <span className="monitoring-badge">Monitoring</span>
              </div>
            </section>

            <section className="authority-panel">
              <div className="panel-heading-row">
                <div><p className="eyebrow">RESOLUTION EVIDENCE</p><h2>Submit field evidence</h2></div>
              </div>
              <div className="evidence-dropzone">
                <div className="evidence-icon">+</div>
                <div><strong>Add repair evidence</strong><p>Upload a before/after photo or supporting field evidence for AI-assisted verification.</p></div>
                <button className="secondary-button" onClick={() => showToast("Demo: evidence upload opened")}>Choose Evidence</button>
              </div>
            </section>
          </div>

          <aside className="authority-side-column">
            <section className="authority-panel authority-status-panel">
              <p className="eyebrow">CURRENT STATUS</p>
              <div className="large-status">{issue.status}</div>
              <p>Last updated {issue.updated}. Citizen reports remain linked to this Master Civic Issue.</p>
            </section>
            <section className="authority-panel">
              <p className="eyebrow">LIFECYCLE</p>
              <div className="authority-timeline">
                <div><span /><div><strong>Reports combined</strong><small>{issue.reports} citizen reports linked</small></div></div>
                <div><span /><div><strong>Assigned</strong><small>{issue.department}</small></div></div>
                <div className="current"><span /><div><strong>{issue.status}</strong><small>Current workflow state</small></div></div>
              </div>
            </section>
            <section className="authority-panel">
              <p className="eyebrow">COMMUNITY SIGNAL</p>
              <h3>{issue.reports} citizen reports</h3>
              <p>Independent reports can be grouped when they describe the same civic problem and location.</p>
              <button className="secondary-button full-width" onClick={() => showToast("Demo: citizen reports panel opened")}>View Citizen Reports</button>
            </section>
          </aside>
        </section>
      </div>
    </main>
  );
}

function ComplaintsTab({ issues, onSelect }) {
  return (
    <section className="authority-tab-page">
      <section className="authority-welcome">
        <div>
          <p className="eyebrow">COMPLAINT MANAGEMENT</p>
          <h1>Active civic issues requiring attention.</h1>
          <p>Review Master Civic Issues, understand community reports, and manage the resolution workflow.</p>
        </div>
        <div className="authority-live-status"><span className="live-dot" /><strong>128 open issues</strong><small>Demo operational data</small></div>
      </section>

      <section className="authority-panel">
        <div className="panel-heading-row">
          <div><p className="eyebrow">MASTER ISSUE QUEUE</p><h2>Active civic issues</h2></div>
          <span className="authority-count-badge">{issues.length} master issues</span>
        </div>
        <div className="complaints-grid">
          {issues.map((issue) => (
            <button key={issue.id} className="complaint-card" onClick={() => onSelect(issue.id)}>
              <div className="complaint-card-top">
                <span className={`authority-priority ${slug(issue.priority)}`}>{issue.priority} priority</span>
                <span className={`authority-status ${slug(issue.status)}`}>{issue.status}</span>
              </div>
              <h3>{issue.title}</h3>
              <p>{issue.location}</p>
              <div className="complaint-card-meta"><span><strong>{issue.reports}</strong> citizen reports</span><span>{issue.department}</span></div>
              <span className="complaint-card-link">Review issue →</span>
            </button>
          ))}
        </div>
      </section>

      <section className="authority-panel">
        <div className="panel-heading-row"><div><p className="eyebrow">REPORT LIFECYCLE</p><h2>How complaints move through CivicResolve</h2></div></div>
        <div className="lifecycle-strip">
          <div><b>01</b><strong>Citizen report</strong><span>Photo, description and location</span></div>
          <div><b>02</b><strong>AI review</strong><span>Classify and structure the issue</span></div>
          <div><b>03</b><strong>Issue fusion</strong><span>Group related reports</span></div>
          <div><b>04</b><strong>Department action</strong><span>Assign, repair and verify</span></div>
        </div>
      </section>
    </section>
  );
}

function MapTab({ issues, onSelect }) {
  return (
    <section className="authority-tab-page">
      <section className="authority-welcome">
        <div>
          <p className="eyebrow">CIVIC ISSUE MAP</p>
          <h1>Where civic issues are being reported.</h1>
          <p>Explore approximate issue locations, identify clusters, and open a Master Civic Issue for review.</p>
        </div>
        <div className="authority-live-status"><span className="live-dot" /><strong>128 mapped issues</strong><small>Approximate demo locations</small></div>
      </section>

      <section className="authority-panel authority-full-map-panel">
        <div className="panel-heading-row">
          <div><p className="eyebrow">ISSUE LOCATIONS</p><h2>Reported civic problems</h2></div>
          <div className="map-filter-pills"><span>All</span><span>High priority</span><span>In progress</span></div>
        </div>
        <IssueMap issues={issues} onSelect={onSelect} large />
      </section>

      <section className="authority-panel">
        <div className="panel-heading-row"><div><p className="eyebrow">MAP SUMMARY</p><h2>Active locations</h2></div></div>
        <div className="map-location-list">
          {issues.map((issue) => (
            <button key={issue.id} onClick={() => onSelect(issue.id)}>
              <span className={`impact-priority-dot ${slug(issue.priority)}`} />
              <div><strong>{issue.title}</strong><small>{issue.location} · {issue.reports} reports</small></div>
              <b>→</b>
            </button>
          ))}
        </div>
      </section>
    </section>
  );
}

function OverviewTab({ issues, onSelect, showToast }) {
  return (
    <>
      <section className="authority-welcome">
        <div>
          <p className="eyebrow">CIVIC OPERATIONS OVERVIEW</p>
          <h1>Good afternoon, Road Maintenance.</h1>
          <p>Monitor community reports, coordinate department action, and verify civic issue resolution from one workspace.</p>
        </div>
        <div className="authority-live-status"><span className="live-dot" /><strong>System monitoring active</strong><small>Updated just now</small></div>
      </section>

      <section className="authority-stat-grid authority-impact-stats">
        <div className="authority-stat impact-blue"><span>Total open issues</span><strong>128</strong><small>Across all departments</small><b>↑ 8 this week</b></div>
        <div className="authority-stat impact-red"><span>High priority</span><strong>14</strong><small>Requires attention</small><b>6 due today</b></div>
        <div className="authority-stat impact-amber"><span>In progress</span><strong>37</strong><small>Currently being handled</small><b>12 updated today</b></div>
        <div className="authority-stat impact-green"><span>Resolved</span><strong>52</strong><small>This reporting period</small><b>41 verified</b></div>
      </section>

      <section className="authority-command-grid">
        <section className="authority-panel authority-priority-panel">
          <div className="panel-heading-row"><div><p className="eyebrow">REQUIRES ATTENTION</p><h2>Priority civic issues</h2></div><span className="authority-count-badge">3 active</span></div>
          <div className="impact-issue-list">
            {issues.map((issue) => (
              <button key={issue.id} className="impact-issue-item" onClick={() => onSelect(issue.id)}>
                <span className={`impact-priority-dot ${slug(issue.priority)}`} />
                <span className="impact-issue-copy"><strong>{issue.title}</strong><small>{issue.id} · {issue.location}</small><em>{issue.reports} citizen reports · {issue.department}</em></span>
                <span className="impact-issue-status">{issue.status}<b>→</b></span>
              </button>
            ))}
          </div>
        </section>

        <section className="authority-panel authority-map-panel">
          <div className="panel-heading-row"><div><p className="eyebrow">CIVIC ISSUE MAP</p><h2>Where issues are being reported</h2></div><span className="map-count">128 issues</span></div>
          <IssueMap issues={issues} onSelect={onSelect} />
        </section>
      </section>

      <section className="authority-insights-grid">
        <section className="authority-panel">
          <div className="panel-heading-row"><div><p className="eyebrow">CIVIC INTELLIGENCE</p><h2>Issue categories</h2></div><span className="workflow-note">Current period</span></div>
          <div className="category-bars">
            {categoryData.map(([label, value]) => (
              <div className="category-bar-row" key={label}>
                <div><span>{label}</span><strong>{value}</strong></div>
                <div className="category-track"><i style={{ width: `${value}%` }} /></div>
              </div>
            ))}
          </div>
        </section>

        <section className="authority-panel intelligence-panel">
          <div className="panel-heading-row"><div><p className="eyebrow">AI-GENERATED SIGNALS</p><h2>What needs attention?</h2></div><span className="authority-ai-badge">AI assisted</span></div>
          <div className="signal-list">
            <div><span className="signal-icon">!</span><p><strong>Recurring hotspot</strong><small>3 unresolved issues are clustered near the same road corridor.</small></p></div>
            <div><span className="signal-icon">↗</span><p><strong>Community reports increasing</strong><small>Road-damage reports are showing a recent increase in this reporting period.</small></p></div>
            <div><span className="signal-icon">✓</span><p><strong>Verification queue</strong><small>6 resolved issues are waiting for evidence review.</small></p></div>
          </div>
        </section>
      </section>

      <section className="authority-lower-grid">
        <section className="authority-panel">
          <div className="panel-heading-row"><div><p className="eyebrow">MASTER CIVIC ISSUES</p><h2>Active issue queue</h2></div><button className="text-action" onClick={() => showToast("Open Complaints tab to view the full queue")}>View all →</button></div>
          <div className="authority-table-wrap">
            <table className="authority-table impact-table">
              <thead><tr><th>Master issue</th><th>Reports</th><th>Priority</th><th>Status</th><th /></tr></thead>
              <tbody>
                {issues.map((issue) => (
                  <tr key={issue.id}>
                    <td><strong>{issue.title}</strong><small>{issue.id} · {issue.category}</small></td>
                    <td>{issue.reports}</td>
                    <td><span className={`authority-priority ${slug(issue.priority)}`}>{issue.priority}</span></td>
                    <td><span className={`authority-status ${slug(issue.status)}`}>{issue.status}</span></td>
                    <td><button className="table-action" onClick={() => onSelect(issue.id)}>Review</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="authority-side-column">
          <section className="authority-panel">
            <div className="panel-heading-row"><div><p className="eyebrow">RECENT ACTIVITY</p><h2>Latest updates</h2></div></div>
            <div className="activity-list">
              {activity.map(([time, title, text]) => (
                <div className="activity-item" key={`${time}-${title}`}><time>{time}</time><strong>{title}</strong><p>{text}</p></div>
              ))}
            </div>
          </section>
          <section className="authority-panel">
            <p className="eyebrow">AGENT MONITORING</p>
            <h2>Lifecycle automation</h2>
            <div className="agent-monitor-row"><span className="agent-dot" /><div><strong>Follow-up agent</strong><small>Monitoring 37 active issues</small></div></div>
            <div className="agent-monitor-row"><span className="agent-dot" /><div><strong>Verification agent</strong><small>Waiting for 6 evidence submissions</small></div></div>
            <div className="agent-monitor-row"><span className="agent-dot" /><div><strong>Pattern intelligence</strong><small>3 recurring hotspots detected</small></div></div>
          </section>
        </aside>
      </section>
    </>
  );
}

export default function AuthorityDashboard({ onBack }) {
  const [issues, setIssues] = useState(initialIssues);
  const [selectedIssueId, setSelectedIssueId] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [toast, setToast] = useState("");

  const selectedIssue = issues.find((issue) => issue.id === selectedIssueId);

  const showToast = (message) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2200);
  };

  if (selectedIssue) {
    return (
      <>
        {toast && <div className="authority-toast">{toast}</div>}
        <IssueDetail
          issue={selectedIssue}
          issues={issues}
          setIssues={setIssues}
          onBack={() => setSelectedIssueId(null)}
          showToast={showToast}
        />
      </>
    );
  }

  return (
    <main className="authority-page authority-impact-page">
      {toast && <div className="authority-toast">{toast}</div>}
      <AuthorityHeader onBack={onBack} />

      <div className="authority-shell">
        <nav className="authority-tabs" aria-label="Authority sections">
          <button className={activeTab === "overview" ? "active" : ""} onClick={() => setActiveTab("overview")}>Overview</button>
          <button className={activeTab === "complaints" ? "active" : ""} onClick={() => setActiveTab("complaints")}>Complaints</button>
          <button className={activeTab === "map" ? "active" : ""} onClick={() => setActiveTab("map")}>Map</button>
        </nav>

        {activeTab === "overview" && <OverviewTab issues={issues} onSelect={setSelectedIssueId} showToast={showToast} />}
        {activeTab === "complaints" && <ComplaintsTab issues={issues} onSelect={setSelectedIssueId} />}
        {activeTab === "map" && <MapTab issues={issues} onSelect={setSelectedIssueId} />}
      </div>
    </main>
  );
}
