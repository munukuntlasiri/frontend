import { useEffect, useState } from "react";

const DEMO_CREDENTIALS = {
  officerId: "RM-DEMO-01",
  password: "demo123",
  department: "Road Maintenance",
};

function AuthorityLogin({ onBack, onLogin }) {
  const [officerId, setOfficerId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [rememberMe, setRememberMe] = useState(() => localStorage.getItem("civicresolve-remember-authority") === "true");

  useEffect(() => {
    const saved = localStorage.getItem("civicresolve-authority-demo");
    if (!saved) return;

    try {
      const parsed = JSON.parse(saved);
      if (parsed.officerId) setOfficerId(parsed.officerId);
      if (parsed.password) setPassword(parsed.password);
    } catch {
      localStorage.removeItem("civicresolve-authority-demo");
    }
  }, []);

  const handleSubmit = (event) => {
    event.preventDefault();
    setError("");

    if (
      officerId.trim() === DEMO_CREDENTIALS.officerId &&
      password === DEMO_CREDENTIALS.password
    ) {
      sessionStorage.setItem(
        "civicresolve-authority",
        JSON.stringify({
          officerId: DEMO_CREDENTIALS.officerId,
          department: DEMO_CREDENTIALS.department,
        })
      );
      if (rememberMe) {
        localStorage.setItem("civicresolve-remember-authority", "true");
        localStorage.setItem("civicresolve-authority-demo", JSON.stringify({
          officerId: DEMO_CREDENTIALS.officerId,
          password: DEMO_CREDENTIALS.password,
        }));
      } else {
        localStorage.removeItem("civicresolve-remember-authority");
        localStorage.removeItem("civicresolve-authority-demo");
      }
      onLogin();
      return;
    }

    setError("The officer ID or password is incorrect.");
  };

  return (
    <main className="authority-login-page">
      <header className="service-header">
        <button className="back-button" onClick={onBack}>
          ← Back to CivicResolve
        </button>

        <div className="service-brand">
          <strong>CivicResolve</strong>
          <span>Authority Portal</span>
        </div>
      </header>

      <section className="authority-login-shell">
        <div className="authority-login-intro">
          <p className="eyebrow">OFFICIAL AUTHORITY ACCESS</p>
          <h1>Sign in to the Authority Portal</h1>
          <p>
            Access assigned civic issues, department work queues, citizen
            reports, and resolution workflows.
          </p>
        </div>

        <form className="authority-login-card" onSubmit={handleSubmit}>
          <div className="authority-login-card-header">
            <span className="authority-shield">✓</span>
            <div>
              <strong>Department sign in</strong>
              <span>Use your official authority credentials.</span>
            </div>
          </div>

          <label className="field-label" htmlFor="officer-id">
            Officer ID
          </label>
          <input
            id="officer-id"
            className="service-input"
            value={officerId}
            onChange={(event) => setOfficerId(event.target.value)}
            placeholder="Enter officer ID"
            autoComplete="username"
          />

          <label className="field-label" htmlFor="authority-password">
            Password
          </label>
          <input
            id="authority-password"
            className="service-input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter password"
            autoComplete="current-password"
          />

          {error && <div className="service-notice error">{error}</div>}

          <label className="remember-authority">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(event) => setRememberMe(event.target.checked)}
            />
            <span>Remember me on this device</span>
          </label>

          <button className="primary-button full-width" type="submit">
            Sign in
          </button>

          <div className="demo-credentials">
            <span>Demo credentials for the prototype</span>
            <strong>RM-DEMO-01</strong>
            <strong>demo123</strong>
          </div>
        </form>
      </section>
    </main>
  );
}

export default AuthorityLogin;
