const socket = io();

const $ = (id) => document.getElementById(id);
let role = null;
let roomCode = null;
let playerName = null;
let hostToken = null;
let currentState = null;
let hasSubmitted = false;

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("show");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => el.classList.remove("show"), 3200);
}

function showGame() {
  $("entry-panel").classList.add("hidden");
  $("game-panel").classList.remove("hidden");
  $("room-code-display").textContent = roomCode || "-----";
  $("name-display").textContent = playerName || "—";
  $("player-panel").classList.toggle("hidden", role !== "player");
  $("host-panel").classList.toggle("hidden", role !== "host");
}

function sendHostAction(action, extra = {}) {
  if (role !== "host" || !hostToken) {
    toast("Only the host can do that.");
    return;
  }
  socket.emit("host_action", { action, host_token: hostToken, ...extra });
}

$("create-button").addEventListener("click", () => {
  playerName = $("player-name").value.trim() || "Host";
  socket.emit("create_room", { name: playerName });
});

$("join-button").addEventListener("click", () => {
  playerName = $("player-name").value.trim();
  roomCode = $("room-code").value.trim().toUpperCase();
  if (!playerName) return toast("Please enter your name.");
  if (!roomCode) return toast("Enter the room code from your host.");
  socket.emit("join_room", { name: playerName, code: roomCode });
});

$("room-code").addEventListener("input", (event) => {
  event.target.value = event.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 5);
});

$("answer-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const answer = $("answer-input").value.trim();
  if (!answer) return toast("Enter an answer first.");
  socket.emit("submit_answer", { answer });
});

$("next-question-button").addEventListener("click", () => {
  sendHostAction("next_question");
});
$("reveal-button").addEventListener("click", () => sendHostAction("reveal"));
$("hide-button").addEventListener("click", () => sendHostAction("hide"));
$("reset-button").addEventListener("click", () => {
  if (window.confirm("Reset all answers for this question? This cannot be undone.")) {
    sendHostAction("reset");
  }
});
$("leave-button").addEventListener("click", () => window.location.reload());

socket.on("room_created", (data) => {
  role = "host";
  roomCode = data.code;
  hostToken = data.host_token;
  playerName = data.name;
  showGame();
  toast(`Room created! Share code ${roomCode} with your players.`);
});

socket.on("joined_room", (data) => {
  role = "player";
  roomCode = data.code;
  playerName = data.name;
  hasSubmitted = false;
  showGame();
  toast(`Joined room ${roomCode}.`);
});

socket.on("notice", (data) => toast(data.message));
socket.on("submission_saved", (data) => {
  hasSubmitted = true;
  $("answer-input").value = "";
  $("submission-message").textContent = data.message + " You can update it until submissions are locked.";
  toast(data.message);
});

socket.on("state", (state) => {
  currentState = state;
  if (roomCode && state.code !== roomCode) return;
  $("room-code-display").textContent = state.code;
  $("question-number").textContent = state.question_number;
  $("counts").textContent = `${state.answer_count} of ${state.player_count} submitted`;

  const list = $("players-list");
  list.replaceChildren();
  state.players.forEach((player) => {
    const li = document.createElement("li");
    const left = document.createElement("span");
    left.className = "player-name";
    left.textContent = player.name;
    const right = document.createElement("span");
    right.className = "player-answer";
    if (state.revealed) {
      right.textContent = player.answer ?? (player.submitted ? "—" : "No answer");
    } else {
      right.textContent = player.submitted ? "Submitted ✓" : "Waiting…";
      right.className += player.submitted ? " submitted" : " waiting";
    }
    li.append(left, right);
    list.append(li);
  });

  if (role === "player") {
    $("submit-button").disabled = state.locked || state.revealed;
    $("answer-input").disabled = state.locked || state.revealed;
    if (state.locked || state.revealed) {
      $("submission-message").textContent = "Submissions are closed for this question.";
    } else if (state.players.find(p => p.name === playerName)?.submitted) {
      $("submission-message").textContent = "Answer received. Submit again to update it before lock.";
    }
  }
});

socket.on("connect_error", () => toast("Connection problem. Refresh and try again."));
