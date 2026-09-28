import { useEffect, useRef, useState } from "react";

const ISSUE_TYPES = [
  "Road damage",
  "Waste",
  "Water",
  "Streetlight",
  "Drainage",
  "Public safety",
  "Other",
];

const initialForm = {
  issueType: "",
  description: "",
  location: "",
};

function ReportIssue({ onBack }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(initialForm);
  const [locationStatus, setLocationStatus] = useState("not-started");
  const [locationLabel, setLocationLabel] = useState("");
  const [photoFiles, setPhotoFiles] = useState([]);
  const [videoFiles, setVideoFiles] = useState([]);
  const [recordedVideo, setRecordedVideo] = useState(null);
  const [recordedAudio, setRecordedAudio] = useState(null);
  const [isVideoRecording, setIsVideoRecording] = useState(false);
  const [isAudioRecording, setIsAudioRecording] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [submittedId, setSubmittedId] = useState("");

  const videoInputRef = useRef(null);
  const photoInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const videoPreviewRef = useRef(null);
  const cameraStreamRef = useRef(null);
  const videoRecorderRef = useRef(null);
  const audioRecorderRef = useRef(null);
  const videoChunksRef = useRef([]);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    return () => {
      cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
      if (recordedVideo?.url) URL.revokeObjectURL(recordedVideo.url);
      if (recordedAudio?.url) URL.revokeObjectURL(recordedAudio.url);
    };
  }, [recordedVideo, recordedAudio]);

  const updateForm = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const requestLocation = () => {
    if (!navigator.geolocation) {
      setLocationStatus("unsupported");
      return;
    }

    setLocationStatus("loading");

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setLocationStatus("success");
        setLocationLabel(`${latitude.toFixed(5)}, ${longitude.toFixed(5)}`);
        setForm((current) => ({
          ...current,
          location: `${latitude}, ${longitude}`,
        }));
      },
      () => {
        setLocationStatus("error");
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const handlePhotos = (event) => {
    const files = Array.from(event.target.files || []).filter((file) =>
      file.type.startsWith("image/")
    );
    setPhotoFiles((current) => [...current, ...files].slice(0, 5));
    event.target.value = "";
  };

  const handleVideos = (event) => {
    const files = Array.from(event.target.files || []).filter((file) =>
      file.type.startsWith("video/")
    );
    setVideoFiles((current) => [...current, ...files].slice(0, 3));
    event.target.value = "";
  };

  const removePhoto = (index) => {
    setPhotoFiles((current) => current.filter((_, i) => i !== index));
  };

  const removeVideo = (index) => {
    setVideoFiles((current) => current.filter((_, i) => i !== index));
  };

  const startVideoRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setVideoFiles((current) => current);
      alert("Video recording is not supported in this browser. You can upload a video instead.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: true,
      });

      cameraStreamRef.current = stream;
      setIsVideoRecording(true);

      if (videoPreviewRef.current) {
        videoPreviewRef.current.srcObject = stream;
        await videoPreviewRef.current.play();
      }

      videoChunksRef.current = [];
      const recorder = new MediaRecorder(stream, { mimeType: "video/webm" });
      videoRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) videoChunksRef.current.push(event.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(videoChunksRef.current, { type: "video/webm" });
        const url = URL.createObjectURL(blob);
        setRecordedVideo({ blob, url, name: `civic-video-${Date.now()}.webm` });

        stream.getTracks().forEach((track) => track.stop());
        cameraStreamRef.current = null;
        setIsVideoRecording(false);
      };

      recorder.start();
    } catch {
      setIsVideoRecording(false);
      alert("Camera access was not available. Please allow camera access or upload a video.");
    }
  };

  const stopVideoRecording = () => {
    if (videoRecorderRef.current?.state !== "inactive") {
      videoRecorderRef.current.stop();
    }
  };

  const startAudioRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      alert("Voice recording is not supported in this browser. You can type your description instead.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      audioRecorderRef.current = recorder;
      setIsAudioRecording(true);

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const url = URL.createObjectURL(blob);
        setRecordedAudio({ blob, url, name: `civic-voice-${Date.now()}.webm` });
        stream.getTracks().forEach((track) => track.stop());
        setIsAudioRecording(false);
      };

      recorder.start();
    } catch {
      setIsAudioRecording(false);
      alert("Microphone access was not available. Please allow microphone access or type your description.");
    }
  };

  const stopAudioRecording = () => {
    if (audioRecorderRef.current?.state !== "inactive") {
      audioRecorderRef.current.stop();
    }
  };

  const buildAnalysis = () => {
    const issueType = form.issueType || "Civic issue";
    const description =
      form.description.trim() ||
      "Citizen submitted an issue with supporting evidence.";

    const priority =
      issueType === "Public safety" || issueType === "Road damage"
        ? "High"
        : "Medium";

    const departmentMap = {
      "Road damage": "Road Maintenance",
      Waste: "Sanitation",
      Water: "Water Supply",
      Streetlight: "Electrical Services",
      Drainage: "Drainage & Public Works",
      "Public safety": "Public Safety",
      Other: "Civic Services",
    };

    setAnalysis({
      type: issueType,
      priority,
      department: departmentMap[issueType] || "Civic Services",
      summary: description,
      evidenceCount:
        photoFiles.length + videoFiles.length + (recordedVideo ? 1 : 0),
    });
    setStep(4);
  };

  const canContinueStep1 = form.issueType && form.description.trim().length >= 8;
  const hasEvidence =
    photoFiles.length > 0 ||
    videoFiles.length > 0 ||
    Boolean(recordedVideo) ||
    Boolean(recordedAudio);

  const submitReport = () => {
    const id = `CR-2026-${Math.floor(1000 + Math.random() * 9000)}`;
    setSubmittedId(id);
    setStep(5);
  };

  return (
    <main className="report-page">
      <header className="service-header">
        <button className="back-button" onClick={onBack}>
          ← Back
        </button>

        <div className="service-brand">
          <strong>CivicResolve</strong>
          <span>Citizen Service</span>
        </div>
      </header>

      <section className="report-shell">
        {step < 5 && (
          <div className="report-progress" aria-label={`Step ${step} of 4`}>
            <div>
              <span>Report an Issue</span>
              <strong>Step {step} of 4</strong>
            </div>
            <div className="progress-track">
              <span style={{ width: `${step * 25}%` }} />
            </div>
          </div>
        )}

        {step === 1 && (
          <section className="report-step">
            <div className="page-heading">
              <p className="eyebrow">STEP 1 · ISSUE DETAILS</p>
              <h1>What would you like to report?</h1>
              <p>
                Tell us what is happening. You can add evidence and location
                details in the next steps.
              </p>
            </div>

            <div className="service-form-card">
              <label className="field-label" htmlFor="issue-type">
                Issue type
              </label>
              <select
                id="issue-type"
                className="service-input"
                value={form.issueType}
                onChange={(event) => updateForm("issueType", event.target.value)}
              >
                <option value="">Select an issue type</option>
                {ISSUE_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>

              <label className="field-label" htmlFor="issue-description">
                Describe the issue
              </label>
              <textarea
                id="issue-description"
                className="service-input service-textarea"
                value={form.description}
                onChange={(event) =>
                  updateForm("description", event.target.value)
                }
                placeholder="For example: A large pothole is making it difficult for vehicles to pass safely."
                rows={6}
              />

              <div className="field-help">
                Please avoid sharing private information that is not needed to
                resolve the issue.
              </div>

              <div className="report-actions">
                <button className="primary-button" disabled={!canContinueStep1} onClick={() => setStep(2)}>
                  Continue
                </button>
              </div>
            </div>
          </section>
        )}

        {step === 2 && (
          <section className="report-step">
            <div className="page-heading">
              <p className="eyebrow">STEP 2 · LOCATION</p>
              <h1>Where is the issue?</h1>
              <p>
                Your location helps us send the report to the appropriate
                local department.
              </p>
            </div>

            <div className="location-service-card">
              <div className="location-icon">⌖</div>
              <div>
                <strong>Use my current location</strong>
                <p>
                  CivicResolve will use your device location only to identify
                  where the issue was reported.
                </p>
              </div>
              <button className="secondary-button" onClick={requestLocation}>
                {locationStatus === "loading"
                  ? "Detecting..."
                  : locationStatus === "success"
                    ? "Location detected"
                    : "Use current location"}
              </button>
            </div>

            {locationStatus === "success" && (
              <div className="location-result">
                <span>✓</span>
                <div>
                  <strong>Location captured</strong>
                  <small>{locationLabel}</small>
                </div>
              </div>
            )}

            {locationStatus === "error" && (
              <div className="service-notice error">
                We could not access your location. You can continue and add
                the location later.
              </div>
            )}

            <div className="report-actions">
              <button className="secondary-button" onClick={() => setStep(1)}>
                Back
              </button>
              <button className="primary-button" onClick={() => setStep(3)}>
                Continue
              </button>
            </div>
          </section>
        )}

        {step === 3 && (
          <section className="report-step">
            <div className="page-heading">
              <p className="eyebrow">STEP 3 · EVIDENCE</p>
              <h1>Add photos or video</h1>
              <p>
                Evidence is optional, but photos and video can help the
                responsible department understand the problem.
              </p>
            </div>

            <div className="evidence-options">
              <button className="evidence-action" onClick={() => cameraInputRef.current?.click()}>
                <span className="evidence-action-icon">📷</span>
                <strong>Take a photo</strong>
                <small>Use your device camera</small>
              </button>

              <button className="evidence-action" onClick={() => photoInputRef.current?.click()}>
                <span className="evidence-action-icon">🖼️</span>
                <strong>Choose photo</strong>
                <small>Select from your device</small>
              </button>

              <button className="evidence-action" onClick={startVideoRecording}>
                <span className="evidence-action-icon">🎥</span>
                <strong>{isVideoRecording ? "Recording video..." : "Record video"}</strong>
                <small>{isVideoRecording ? "Tap to stop recording" : "Record the issue now"}</small>
              </button>

              <button className="evidence-action" onClick={() => videoInputRef.current?.click()}>
                <span className="evidence-action-icon">📁</span>
                <strong>Upload video</strong>
                <small>Choose an existing video</small>
              </button>
            </div>

            {isVideoRecording && (
              <div className="recording-panel">
                <div className="recording-header">
                  <div>
                    <span className="recording-dot" />
                    <strong>Video recording</strong>
                  </div>
                  <button className="danger-button" onClick={stopVideoRecording}>
                    Stop recording
                  </button>
                </div>
                <video ref={videoPreviewRef} className="camera-preview" muted playsInline />
              </div>
            )}

            <input
              ref={cameraInputRef}
              className="visually-hidden"
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handlePhotos}
            />

            <input
              ref={photoInputRef}
              className="visually-hidden"
              type="file"
              accept="image/*"
              multiple
              onChange={handlePhotos}
            />

            <input
              ref={videoInputRef}
              className="visually-hidden"
              type="file"
              accept="video/*"
              multiple
              onChange={handleVideos}
            />

            <div className="voice-card">
              <div>
                <strong>Prefer speaking?</strong>
                <p>Record a short voice description. The AI service can transcribe it later.</p>
              </div>
              <button
                className={isAudioRecording ? "danger-button" : "secondary-button"}
                onClick={isAudioRecording ? stopAudioRecording : startAudioRecording}
              >
                {isAudioRecording ? "Stop voice recording" : "🎙️ Record voice"}
              </button>
            </div>

            {(photoFiles.length > 0 || videoFiles.length > 0 || recordedVideo || recordedAudio) && (
              <div className="evidence-list">
                <div className="section-label">Selected evidence</div>

                {photoFiles.map((file, index) => (
                  <div className="evidence-file" key={`${file.name}-${index}`}>
                    <span>📷</span>
                    <div>
                      <strong>{file.name}</strong>
                      <small>Photo</small>
                    </div>
                    <button onClick={() => removePhoto(index)} aria-label={`Remove ${file.name}`}>
                      Remove
                    </button>
                  </div>
                ))}

                {videoFiles.map((file, index) => (
                  <div className="evidence-file" key={`${file.name}-${index}`}>
                    <span>🎥</span>
                    <div>
                      <strong>{file.name}</strong>
                      <small>Video</small>
                    </div>
                    <button onClick={() => removeVideo(index)} aria-label={`Remove ${file.name}`}>
                      Remove
                    </button>
                  </div>
                ))}

                {recordedVideo && (
                  <div className="evidence-file">
                    <span>🎥</span>
                    <div>
                      <strong>{recordedVideo.name}</strong>
                      <small>Recorded video</small>
                    </div>
                    <button onClick={() => setRecordedVideo(null)}>Remove</button>
                  </div>
                )}

                {recordedAudio && (
                  <div className="evidence-file">
                    <span>🎙️</span>
                    <div>
                      <strong>{recordedAudio.name}</strong>
                      <small>Voice description</small>
                    </div>
                    <button onClick={() => setRecordedAudio(null)}>Remove</button>
                  </div>
                )}
              </div>
            )}

            {!hasEvidence && (
              <div className="service-notice">
                Evidence is optional. You can continue without attaching a
                photo or video.
              </div>
            )}

            <div className="report-actions">
              <button className="secondary-button" onClick={() => setStep(2)}>
                Back
              </button>
              <button className="primary-button" onClick={buildAnalysis}>
                Review report
              </button>
            </div>
          </section>
        )}

        {step === 4 && analysis && (
          <section className="report-step">
            <div className="page-heading">
              <p className="eyebrow">STEP 4 · REVIEW</p>
              <h1>Review your report</h1>
              <p>
                Check the information before sending it to CivicResolve.
              </p>
            </div>

            <div className="review-card">
              <div className="review-header">
                <div>
                  <span className="review-label">AI-assisted classification</span>
                  <h2>{analysis.type}</h2>
                </div>
                <span className={`priority-badge priority-${analysis.priority.toLowerCase()}`}>
                  {analysis.priority} priority
                </span>
              </div>

              <div className="review-grid">
                <div>
                  <span>Issue description</span>
                  <strong>{analysis.summary}</strong>
                </div>
                <div>
                  <span>Responsible department</span>
                  <strong>{analysis.department}</strong>
                </div>
                <div>
                  <span>Location</span>
                  <strong>{locationLabel || "Location not provided"}</strong>
                </div>
                <div>
                  <span>Evidence</span>
                  <strong>
                    {analysis.evidenceCount
                      ? `${analysis.evidenceCount} attachment${analysis.evidenceCount > 1 ? "s" : ""}`
                      : "No photo or video"}
                  </strong>
                </div>
              </div>

              <div className="service-notice">
                AI classification is an initial assessment. The responsible
                department may update the category or priority after review.
              </div>
            </div>

            <div className="report-actions">
              <button className="secondary-button" onClick={() => setStep(3)}>
                Back
              </button>
              <button className="primary-button" onClick={submitReport}>
                Submit report
              </button>
            </div>
          </section>
        )}

        {step === 5 && (
          <section className="report-success">
            <div className="success-mark">✓</div>
            <p className="eyebrow">REPORT RECEIVED</p>
            <h1>Your report has been submitted.</h1>
            <p>
              Your report has been recorded and can now be routed to the
              responsible civic department.
            </p>

            <div className="complaint-id-card">
              <span>Complaint ID</span>
              <strong>{submittedId}</strong>
              <small>Keep this ID to track your report.</small>
            </div>

            <div className="success-summary">
              <div>
                <span>Issue</span>
                <strong>{analysis?.type}</strong>
              </div>
              <div>
                <span>Department</span>
                <strong>{analysis?.department}</strong>
              </div>
              <div>
                <span>Status</span>
                <strong>Submitted</strong>
              </div>
            </div>

            <div className="report-actions centered">
              <button className="secondary-button" onClick={onBack}>
                Back to CivicResolve
              </button>
            </div>
          </section>
        )}
      </section>
    </main>
  );
}

export default ReportIssue;
