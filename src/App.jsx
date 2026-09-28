import { useEffect, useState } from "react";
import ReportIssue from "./ReportIssue";
import AuthorityDashboard from "./AuthorityDashboard";
import AuthorityLogin from "./AuthorityLogin";

function App() {
  const [currentPage, setCurrentPage] = useState("home");
  const [theme, setTheme] = useState(() =>
    localStorage.getItem("civicresolve-theme") || "light"
  );

  useEffect(() => {
    document.body.classList.toggle("dark-theme", theme === "dark");
    localStorage.setItem("civicresolve-theme", theme);
  }, [theme]);

  const goHome = () => {
    setCurrentPage("home");
  };

  const goToPage = (page) => {
    setCurrentPage(page);
  };

  if (currentPage === "report") {
    return <ReportIssue onBack={goHome} />;
  }

  if (currentPage === "authority-login") {
    return (
      <AuthorityLogin
        onBack={goHome}
        onLogin={() => setCurrentPage("authority")}
      />
    );
  }

  if (currentPage === "authority") {
    return <AuthorityDashboard onBack={goHome} />;
  }

  if (currentPage === "reports") {
    return (
      <main className="reports-page">
        <button className="back-button" onClick={goHome}>
          ← Back to home
        </button>

        <section className="reports-container">
          <div className="page-heading">
            <p className="eyebrow">MY REPORTS</p>

            <h2>Track your civic reports</h2>

            <p>
              See the status of issues you have reported and follow their
              progress.
            </p>
          </div>

          <div className="report-summary">
            <div className="summary-card">
              <span>Total reports</span>
              <strong>4</strong>
            </div>

            <div className="summary-card">
              <span>In progress</span>
              <strong>2</strong>
            </div>

            <div className="summary-card">
              <span>Resolved</span>
              <strong>1</strong>
            </div>
          </div>

          <div className="my-reports-list">
            <article className="my-report-card">
              <div className="report-card-top">
                <span className="report-category">ROAD</span>
                <span className="status-badge status-progress">
                  In progress
                </span>
              </div>

              <h3>Large pothole on main road</h3>

              <p>
                Road damage reported near the main residential road.
              </p>

              <div className="report-meta">
                <span>Report ID: CR-2026-0147</span>
                <span>Reported 2 days ago</span>
              </div>

              <div className="report-timeline">
                <div className="timeline-step completed">
                  <span></span>

                  <div>
                    <strong>Report submitted</strong>
                    <small>2 days ago</small>
                  </div>
                </div>

                <div className="timeline-step completed">
                  <span></span>

                  <div>
                    <strong>Assigned to department</strong>
                    <small>1 day ago</small>
                  </div>
                </div>

                <div className="timeline-step current">
                  <span></span>

                  <div>
                    <strong>Repair in progress</strong>
                    <small>Currently being handled</small>
                  </div>
                </div>

                <div className="timeline-step">
                  <span></span>

                  <div>
                    <strong>Resolution verification</strong>
                    <small>Pending</small>
                  </div>
                </div>
              </div>
            </article>

            <article className="my-report-card">
              <div className="report-card-top">
                <span className="report-category">WASTE</span>

                <span className="status-badge status-pending">
                  Submitted
                </span>
              </div>

              <h3>Overflowing waste collection point</h3>

              <p>
                Waste has accumulated around the collection point.
              </p>

              <div className="report-meta">
                <span>Report ID: CR-2026-0161</span>
                <span>Reported yesterday</span>
              </div>
            </article>

            <article className="my-report-card">
              <div className="report-card-top">
                <span className="report-category">
                  STREETLIGHT
                </span>

                <span className="status-badge status-resolved">
                  Resolved
                </span>
              </div>

              <h3>Streetlight not working</h3>

              <p>
                Streetlight near the community park was reported as not
                functioning.
              </p>

              <div className="report-meta">
                <span>Report ID: CR-2026-0134</span>
                <span>Resolved 4 days ago</span>
              </div>
            </article>
          </div>
        </section>
      </main>
    );
  }

  if (currentPage === "nearby") {
    return (
      <main className="nearby-page">
        <button className="back-button" onClick={goHome}>
          ← Back to home
        </button>

        <section className="nearby-container">
          <div className="page-heading">
            <p className="eyebrow">CIVIC ISSUES NEARBY</p>

            <h2>What's happening around you?</h2>

            <p>
              Explore reported civic issues in your area and see where
              multiple reports are pointing to the same problem.
            </p>
          </div>

          <div className="nearby-toolbar">
            <div>
              <strong>Nearby issues</strong>
              <span>12 reports found</span>
            </div>

            <select>
              <option>All issues</option>
              <option>Road damage</option>
              <option>Waste</option>
              <option>Water</option>
              <option>Streetlights</option>
            </select>
          </div>

          <div className="civic-map">
            <div className="map-road road-one"></div>
            <div className="map-road road-two"></div>
            <div className="map-road road-three"></div>

            <div className="map-area area-one">Main Road</div>
            <div className="map-area area-two">
              Residential Area
            </div>
            <div className="map-area area-three">
              Community Park
            </div>

            <button
              className="map-marker marker-high"
              onClick={() => goToPage("master-issue")}
              title="Large pothole"
            >
              !
            </button>

            <button
              className="map-marker marker-road"
              onClick={() => goToPage("master-issue")}
              title="Road issue"
            >
              R
            </button>

            <button
              className="map-marker marker-waste"
              title="Waste issue"
            >
              W
            </button>

            <button
              className="map-marker marker-water"
              title="Water issue"
            >
              W
            </button>

            <button
              className="map-marker marker-light"
              title="Streetlight issue"
            >
              L
            </button>

            <div className="user-location">
              <span></span>
            </div>

            <div className="map-legend">
              <div>
                <span className="legend-dot high"></span>
                High priority
              </div>

              <div>
                <span className="legend-dot normal"></span>
                Other issue
              </div>

              <div>
                <span className="legend-user"></span>
                You
              </div>
            </div>
          </div>

          <div className="nearby-list-section">
            <div className="nearby-list-heading">
              <div>
                <p className="eyebrow">REPORTED ISSUES</p>
                <h3>Sorted by relevance</h3>
              </div>
            </div>

            <div className="nearby-list">
              <article
                className="nearby-issue selected"
                onClick={() => goToPage("master-issue")}
              >
                <div className="nearby-issue-top">
                  <span className="issue-type">ROAD</span>

                  <span className="issue-priority high">
                    High
                  </span>
                </div>

                <h3>Large pothole on main road</h3>

                <p>
                  Multiple citizens have reported the same road damage.
                </p>

                <div className="master-issue">
                  <strong>Master Civic Issue</strong>
                  <span>23 citizen reports combined</span>
                </div>

                <span className="view-issue">
                  View issue details →
                </span>
              </article>

              <article className="nearby-issue">
                <div className="nearby-issue-top">
                  <span className="issue-type">WASTE</span>

                  <span className="issue-priority medium">
                    Medium
                  </span>
                </div>

                <h3>Overflowing waste collection point</h3>

                <p>
                  Reported by 7 citizens in the last 3 days.
                </p>
              </article>

              <article className="nearby-issue">
                <div className="nearby-issue-top">
                  <span className="issue-type">WATER</span>

                  <span className="issue-priority medium">
                    Medium
                  </span>
                </div>

                <h3>Possible water leakage</h3>

                <p>
                  3 reports were submitted from the same area.
                </p>
              </article>
            </div>
          </div>
        </section>
      </main>
    );
  }

  if (currentPage === "master-issue") {
    return (
      <main className="master-page">
        <button
          className="back-button"
          onClick={() => goToPage("nearby")}
        >
          ← Back to nearby issues
        </button>

        <section className="master-container">
          <div className="master-header">
            <div>
              <p className="eyebrow">MASTER CIVIC ISSUE</p>

              <h2>Large pothole on main road</h2>

              <p>
                Multiple citizen reports have been combined because they
                appear to describe the same road damage.
              </p>
            </div>

            <span className="master-status">
              In progress
            </span>
          </div>

          <div className="master-overview">
            <div className="overview-card">
              <span>Citizen reports</span>
              <strong>23</strong>
              <small>Reports combined</small>
            </div>

            <div className="overview-card">
              <span>Priority</span>
              <strong>High</strong>
              <small>Based on reported risk</small>
            </div>

            <div className="overview-card">
              <span>Department</span>
              <strong>Road Maintenance</strong>
              <small>Responsible department</small>
            </div>

            <div className="overview-card">
              <span>Issue age</span>
              <strong>4 days</strong>
              <small>Since first report</small>
            </div>
          </div>

          <div className="master-grid">
            <div className="master-main-column">
              <section className="detail-section">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">ISSUE SUMMARY</p>
                    <h3>What citizens are reporting</h3>
                  </div>
                </div>

                <div className="issue-summary-box">
                  <div className="summary-icon">!</div>

                  <div>
                    <strong>
                      Large pothole creating a road safety concern
                    </strong>

                    <p>
                      Citizens have repeatedly reported significant road
                      damage at the same location. Several reports include
                      photos of the affected area.
                    </p>
                  </div>
                </div>

                <div className="location-detail">
                  <span className="detail-icon">⌖</span>

                  <div>
                    <strong>Approximate location</strong>

                    <p>
                      Main Road, near Residential Area
                    </p>

                    <small>
                      Location is shown approximately to protect citizen
                      privacy.
                    </small>
                  </div>
                </div>
              </section>

              <section className="detail-section">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">EVIDENCE</p>
                    <h3>Citizen-submitted evidence</h3>
                  </div>

                  <span className="evidence-count">
                    8 photos
                  </span>
                </div>

                <div className="evidence-grid">
                  <div className="evidence-placeholder">
                    <span>Road</span>
                    <strong>Pothole evidence</strong>
                  </div>

                  <div className="evidence-placeholder">
                    <span>Road</span>
                    <strong>Surface damage</strong>
                  </div>

                  <div className="evidence-placeholder">
                    <span>Road</span>
                    <strong>Additional report</strong>
                  </div>
                </div>
              </section>

              <section className="detail-section">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">ACTIVITY</p>
                    <h3>Issue timeline</h3>
                  </div>
                </div>

                <div className="master-timeline">
                  <div className="master-timeline-item completed">
                    <span className="timeline-dot"></span>

                    <div>
                      <strong>First report submitted</strong>

                      <p>
                        A citizen reported significant road damage.
                      </p>

                      <small>4 days ago</small>
                    </div>
                  </div>

                  <div className="master-timeline-item completed">
                    <span className="timeline-dot"></span>

                    <div>
                      <strong>Reports combined</strong>

                      <p>
                        Similar reports from the same area were grouped
                        into this master issue.
                      </p>

                      <small>3 days ago</small>
                    </div>
                  </div>

                  <div className="master-timeline-item completed">
                    <span className="timeline-dot"></span>

                    <div>
                      <strong>
                        Assigned to Road Maintenance
                      </strong>

                      <p>
                        The issue was routed to the responsible department.
                      </p>

                      <small>2 days ago</small>
                    </div>
                  </div>

                  <div className="master-timeline-item current">
                    <span className="timeline-dot"></span>

                    <div>
                      <strong>Repair in progress</strong>

                      <p>
                        The responsible department has been notified and
                        the issue is being handled.
                      </p>

                      <small>Current status</small>
                    </div>
                  </div>

                  <div className="master-timeline-item">
                    <span className="timeline-dot"></span>

                    <div>
                      <strong>Resolution verification</strong>

                      <p>
                        After repair evidence is submitted, the issue will
                        be checked before being marked resolved.
                      </p>

                      <small>Pending</small>
                    </div>
                  </div>
                </div>
              </section>
            </div>

            <aside className="master-side-column">
              <section className="side-card">
                <p className="eyebrow">AI FUSION</p>

                <h3>Why these reports were combined</h3>

                <p>
                  Reports were grouped because they describe a similar
                  issue in a nearby location.
                </p>

                <div className="fusion-reasons">
                  <div>
                    <span>✓</span>
                    <p>Similar issue type</p>
                  </div>

                  <div>
                    <span>✓</span>
                    <p>Nearby location</p>
                  </div>

                  <div>
                    <span>✓</span>
                    <p>Similar evidence</p>
                  </div>

                  <div>
                    <span>✓</span>
                    <p>Repeated citizen reports</p>
                  </div>
                </div>

                <small className="demo-note">
                  Demo explanation — final matching will be generated by
                  the CivicResolve backend.
                </small>
              </section>

              <section className="side-card">
                <p className="eyebrow">
                  RESPONSIBLE DEPARTMENT
                </p>

                <h3>Road Maintenance</h3>

                <p>
                  This issue has been routed to the department responsible
                  for road repairs in this area.
                </p>

                <div className="department-status">
                  <span></span>
                  Assigned
                </div>
              </section>

              <section className="side-card">
                <p className="eyebrow">COMMUNITY SIGNAL</p>

                <h3>23 citizens affected</h3>

                <p>
                  Multiple independent reports indicate that this is a
                  recurring problem at the same location.
                </p>

                <button className="secondary-button full-width">
                  View citizen reports
                </button>
              </section>
            </aside>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="app">
      <header className="topbar">
        <div className="brand">CivicResolve</div>

        <nav>
          <button onClick={goHome}>Home</button>

          <button onClick={() => goToPage("reports")}>
            My Reports
          </button>

          <button onClick={() => goToPage("authority-login")}>
            Authority Login
          </button>

          <button
            className="theme-toggle"
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
            title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          >
            {theme === "light" ? "☾" : "☀"}
          </button>
        </nav>
      </header>

      <section className="hero">
        <div className="hero-content">
          <p className="eyebrow">YOUR CITY. YOUR VOICE.</p>

          <h1>Making civic issues easier to resolve.</h1>

          <p className="hero-text">
            Report problems in your community, track their progress,
            and see how citizen reports come together to improve your
            neighbourhood.
          </p>

          <button
            className="primary-button"
            onClick={() => goToPage("report")}
          >
            Report an Issue
          </button>
        </div>
      </section>

      <section className="feature-section">
        <div
          className="feature-card"
          onClick={() => goToPage("report")}
        >
          <span className="feature-icon">+</span>

          <h3>Report an Issue</h3>

          <p>
            Report a civic problem with photo, video, voice, description,
            and location.
          </p>
        </div>

        <div
          className="feature-card"
          onClick={() => goToPage("reports")}
        >
          <span className="feature-icon">✓</span>

          <h3>Track My Reports</h3>

          <p>
            Follow the status of issues you have reported.
          </p>
        </div>

        <div
          className="feature-card"
          onClick={() => goToPage("nearby")}
        >
          <span className="feature-icon">⌖</span>

          <h3>Issues Near Me</h3>

          <p>
            Explore civic problems reported by people around you.
          </p>
        </div>
      </section>

      <footer>
        CivicResolve · Making communities easier to improve.
      </footer>
    </main>
  );
}

export default App;