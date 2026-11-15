(() => {
    "use strict";

    const $ = (id) => document.getElementById(id);
    let lastAssistantReply = "";

    function setMode(mode) {
        const selected = mode === "eva" ? "eva" : "inship";
        document.body.dataset.mode = selected;
        document.querySelectorAll("[data-mode-choice]").forEach((button) => {
            const active = button.dataset.modeChoice === selected;
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", String(active));
        });
        if ($("mode-label")) {
            $("mode-label").textContent = selected === "eva"
                ? "EVA · SUIT SIMULATION"
                : "IN-SHIP · CABIN MONITORING";
        }
        try { localStorage.setItem("orbital-health-mode", selected); } catch (_) {}
    }

    async function refreshEva() {
        try {
            const response = await fetch("/api/dashboard");
            if (!response.ok) return;
            const result = await response.json();
            const latest = result.latest;
            if (!latest) return;

            $("eva-heart-rate").textContent = latest.heart_rate ?? "--";
            $("eva-spo2").textContent = latest.spo2 ?? "--";
            $("eva-temperature").textContent = latest.body_temperature ?? "--";

            let analysis = latest.analysis;
            if (typeof analysis === "string") {
                try { analysis = JSON.parse(analysis); } catch (_) { analysis = null; }
            }
            const state = String(analysis?.overall_status || "unknown").toLowerCase();
            const alert = $("eva-alert");
            alert.className = "eva-alert " + (["warning", "critical"].includes(state) ? state : "");
            alert.textContent = state === "critical"
                ? "CRITICAL ALERT: Stop non-essential activity and follow mission medical protocol."
                : state === "warning"
                    ? "WARNING: Review the biometric indicators and follow crew procedures."
                    : state === "normal"
                        ? "No warning detected in the available experimental indicators."
                        : "Waiting for sufficient telemetry.";
        } catch (error) {
            $("eva-alert").textContent = "Telemetry service temporarily unavailable.";
        }
    }

    function addChatMessage(role, content) {
        const history = $("chat-history");
        const message = document.createElement("p");
        message.className = "chat-message " + role;
        message.textContent = content;
        history.appendChild(message);
        history.scrollTop = history.scrollHeight;
    }

    function speak(text) {
        if (!("speechSynthesis" in window)) {
            $("voice-state").textContent = "Speech synthesis is not available in this browser.";
            return;
        }
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "es-ES";
        const voices = window.speechSynthesis.getVoices();
        const spanishVoice = voices.find((voice) => voice.lang?.toLowerCase().startsWith("es"));
        if (spanishVoice) utterance.voice = spanishVoice;
        utterance.onstart = () => { if ($("voice-state")) $("voice-state").textContent = "Speaking with an installed device voice."; };
        utterance.onend = () => { if ($("voice-state")) $("voice-state").textContent = "Speech output ready."; };
        utterance.onerror = () => { if ($("voice-state")) $("voice-state").textContent = "Speech output failed; text remains available."; };
        window.speechSynthesis.speak(utterance);
    }

    async function loadChatHistory() {
        try {
            const response = await fetch("/api/wellbeing/history?limit=20");
            const result = await response.json();
            if (!result.ok || !result.messages?.length) return;
            $("chat-history").replaceChildren();
            result.messages.forEach((item) => {
                addChatMessage(item.role, item.content);
                if (item.role === "assistant") lastAssistantReply = item.content;
            });
        } catch (_) {}
    }

    async function sendMessage(event) {
        event.preventDefault();
        const field = $("wellbeing-message");
        const message = field.value.trim();
        if (!message) return;
        addChatMessage("user", message);
        field.value = "";
        const submit = $("wellbeing-form").querySelector('button[type="submit"]');
        submit.disabled = true;
        try {
            const response = await fetch("/api/wellbeing/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message })
            });
            const result = await response.json();
            if (!response.ok || !result.ok) throw new Error(result.error || "Unable to send message.");
            lastAssistantReply = result.reply;
            addChatMessage("assistant", result.reply);
        } catch (error) {
            addChatMessage("assistant", "The local wellbeing service is unavailable. Your message was not saved.");
        } finally {
            submit.disabled = false;
            field.focus();
        }
    }

    async function saveCheckin() {
        const mood = Number($("mood-input").value);
        const stress = Number($("stress-input").value);
        const note = $("wellbeing-note").value.trim();
        const feedback = $("checkin-feedback");
        try {
            const response = await fetch("/api/wellbeing/checkin", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mood_score: mood, stress_level: stress, note })
            });
            const result = await response.json();
            if (!response.ok || !result.ok) throw new Error(result.error || "Unable to save check-in.");
            feedback.textContent = "Check-in saved locally.";
            $("wellbeing-note").value = "";
        } catch (error) {
            feedback.textContent = "Could not save the check-in: " + error.message;
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        let initialMode = "inship";
        try { initialMode = localStorage.getItem("orbital-health-mode") || "inship"; } catch (_) {}
        setMode(initialMode);

        document.querySelectorAll("[data-mode-choice]").forEach((button) => {
            button.addEventListener("click", () => setMode(button.dataset.modeChoice));
        });

        $("mood-input").addEventListener("input", (event) => {
            $("mood-output").textContent = event.target.value + " / 10";
        });
        $("stress-input").addEventListener("input", (event) => {
            $("stress-output").textContent = event.target.value + " / 10";
        });
        $("wellbeing-form").addEventListener("submit", sendMessage);
        $("save-checkin").addEventListener("click", saveCheckin);
        $("eva-speak").addEventListener("click", () => {
            speak($("eva-alert").textContent);
        });
        $("speak-last").addEventListener("click", () => {
            if (lastAssistantReply) speak(lastAssistantReply);
        });

        if ("speechSynthesis" in window) {
            $("voice-state").textContent = "Speech synthesis available; uses browser/device voices.";
            window.speechSynthesis.getVoices();
        } else {
            $("voice-state").textContent = "Speech synthesis unavailable in this browser.";
        }
        loadChatHistory();
        refreshEva();
        setInterval(refreshEva, 5000);
    });
})();
