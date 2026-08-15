const tg = window.Telegram.WebApp;
tg.expand();

const user = tg.initDataUnsafe?.user || { id: 123456, username: "test_user" };
const userId = user.id;
const username = user.username || "";

const gemsCountEl = document.getElementById("gemsCount");
const levelEl = document.getElementById("level");
const xpBarEl = document.getElementById("xpBar");
const tapButton = document.getElementById("tapButton");
const floatingTexts = document.getElementById("floatingTexts");
const dailyBtn = document.getElementById("dailyBtn");
const inviteBtn = document.getElementById("inviteBtn");
const missionsList = document.getElementById("missionsList");

let currentUser = null;

async function loadUser() {
  const res = await fetch(`/api/user/${userId}?username=${username}`);
  currentUser = await res.json();
  updateUI();
}

function updateUI() {
  gemsCountEl.textContent = currentUser.gems;
  levelEl.textContent = currentUser.level;
  const xpInLevel = currentUser.xp % 100;
  xpBarEl.style.width = xpInLevel + "%";
}

function spawnFloatingText(text, x, y) {
  const el = document.createElement("div");
  el.className = "floating-text";
  el.textContent = text;
  el.style.left = x + "px";
  el.style.top = y + "px";
  floatingTexts.appendChild(el);
  setTimeout(() => el.remove(), 900);
}

tapButton.addEventListener("click", async (e) => {
  tg.HapticFeedback?.impactOccurred("light");

  const rect = tapButton.getBoundingClientRect();
  const x = (e.clientX || rect.width / 2) - rect.left;
  const y = (e.clientY || rect.height / 2) - rect.top;
  spawnFloatingText("+1", x, y);

  const res = await fetch("/api/tap", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId })
  });
  currentUser = await res.json();
  updateUI();
});

dailyBtn.addEventListener("click", async () => {
  const res = await fetch("/api/daily", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId })
  });
  const data = await res.json();
  currentUser = data.user;
  updateUI();
  if (data.claimed) {
    tg.showAlert("🎁 ۱۰ جم گرفتی!");
  } else {
    tg.showAlert("⏳ امروز قبلاً گرفتی، فردا بیا.");
  }
});

inviteBtn.addEventListener("click", () => {
  tg.showAlert("لینک دعوت رو با دستور /invite توی چت بات بگیر.");
});

async function loadMissions() {
  const res = await fetch(`/api/missions/${userId}`);
  const missions = await res.json();
  missionsList.innerHTML = "";
  missions.forEach(m => {
    const div = document.createElement("div");
    div.className = "mission-item" + (m.completed ? " completed" : "");
    div.innerHTML = `
      <span>${m.title}</span>
      <span class="mission-reward">+${m.reward} 💎</span>
      ${m.completed ? "" : `<button class="mission-btn" data-id="${m.id}">دریافت</button>`}
    `;
    missionsList.appendChild(div);
  });

  document.querySelectorAll(".mission-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const missionId = btn.getAttribute("data-id");
      const res = await fetch("/api/missions/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, mission_id: missionId })
      });
      const data = await res.json();
      currentUser = data.user;
      updateUI();
      loadMissions();
    });
  });
}

loadUser();
loadMissions();
