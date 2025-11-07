async function fetchAgentID() {
  const response = await fetch("/agent_id");
  const { agent_id } = await response.json();
  document.getElementById("agent-id").textContent = agent_id;
}

async function fetchRankings() {
  const response = await fetch("/rankings");
  const rankings = await response.json();
  console.log(rankings)

  const tbody = document.querySelector("#rankings-table tbody");
  tbody.innerHTML = "";

  rankings.forEach((player, index) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${index + 1}</td>
      <td>${player.name}</td>
      <td>${player.wins}</td>
      <td>${player.games}</td>
      <td>${(player.win_rate * 100).toFixed(1)}%</td>
    `;
    tbody.appendChild(tr);
  });
}

async function fetchMatchups() {
  const response = await fetch("/matchups");
  const matchups = await response.json();

  const list = document.getElementById("matchups-list");
  list.innerHTML = "";

  matchups.forEach(([player1, player2]) => {
    const li = document.createElement("li");
    li.textContent = `${player1} vs ${player2}`;
    list.appendChild(li);
  });
}

async function refresh() {
  await Promise.all([fetchRankings(), fetchMatchups()]);
}

async function init() {
  await fetchAgentID();
  await refresh();
  setInterval(refresh, 5000);
}

init();
