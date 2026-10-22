/*
 *
 *  ═══════════════════════════════════════════════════════════════
 *   [USER]: Painho_Dev
 *   [ROLE]: FullStack Developer
 *   [SKILLS]: PHP, JavaScript, React, Node.js, TypeScript
 *   [STATUS]: Criando magia com código... ✨
 *   [MOTTO]: "AS VEZES ME SINTO ASSIM" 🎵
 *   [MOOD]: Café + Code = ❤️
 *  ═══════════════════════════════════════════════════════════════
 *          \   ^__^
 *           \  (oo)\_______
 *              (__)\       )\/\
 *                  ||----w |
 *                  ||     ||
 *
 *  [RESENHA]:
 *  "Vida de dev é assim mesmo -
 *   um bug hoje, um deploy amanhã,
 *   e café pra caramba no caminho!"
 *
 *  [BIO]:
 *  Transformando café em código desde sempre.
 *  Especialista em resolver problemas que nem existiam.
 *  Mestre do Ctrl+C / Ctrl+V com estilo.
 *
 */

(function() {
  const styles = [
    'color: #00ff88',
    'font-weight: bold',
    'font-family: "Courier New", monospace',
    'text-shadow: 0 0 10px #00ff88'
  ].join(';');

  console.log(`%c
 ═══════════════════════════════════════════════════════════════
  [USER]: Painho_Dev
  [ROLE]: FullStack Developer
  [SKILLS]: PHP, JavaScript, React, Node.js, TypeScript
  [STATUS]: Criando magia com código... ✨
  [MOTTO]: "AS VEZES ME SINTO ASSIM" 🎵
  [MOOD]: Café + Code = ❤️
 ═══════════════════════════════════════════════════════════════
         \\   ^__^
          \\  (oo)\\_______
             (__)\\       )\/\
                 ||----w |
                 ||     ||

  [RESENHA]:
  "Vida de dev é assim mesmo -
   um bug hoje, um deploy amanhã,
   e café pra caramba no caminho!"

  [BIO]:
  • Transformando café em código desde sempre
  • Especialista em resolver problemas que nem existiam
  • Mestre do Ctrl+C / Ctrl+V com estilo
  • Sobrevivente de 3h da manhã debugando

  [CURRENTLY]:
  🎧 Ouvindo: Lo-fi beats to code/chill
  ☕ Bebendo: Café número ∞
  🔥 Queimando: A documentação do projeto

  "O código não mente, mas as vezes dá 404 na sanidade!"
`, styles);
})();

// Easter egg: abra o console do navegador para ver a resenha completa.

let eventSource = null;
let soundEnabled = true;
let audioCtx = null;

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initSSE();
  fetchStatus();
  setInterval(fetchStatus, 3000);

  document.getElementById("sound-toggle").addEventListener("change", (e) => {
    soundEnabled = e.target.checked;
  });

  document.getElementById("btn-import-modal").addEventListener("click", openImportModal);
});

// Web Audio API Alarm Tone
function playAlertBeep() {
  if (!soundEnabled) return;
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(880, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.35);

    gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.35);

    osc.connect(gain);
    gain.connect(audioCtx.destination);

    osc.start();
    osc.stop(audioCtx.currentTime + 0.35);
  } catch (e) {
    console.warn("Audio playback error:", e);
  }
}

// Tabs
function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

      btn.classList.add("active");
      const target = btn.getAttribute("data-tab");
      document.getElementById(`tab-${target}`).classList.add("active");
    });
  });
}

// SSE Connection
function initSSE() {
  const liveDot = document.getElementById("live-indicator");
  const connText = document.getElementById("connection-status");

  if (eventSource) {
    eventSource.close();
  }

  eventSource = new EventSource("/api/events");

  eventSource.onopen = () => {
    liveDot.classList.add("connected");
    connText.innerText = "STREAM ATIVO";
  };

  eventSource.onerror = () => {
    liveDot.classList.remove("connected");
    connText.innerText = "Reconectando...";
  };

  eventSource.onmessage = (e) => {
    try {
      const payload = JSON.parse(e.data);
      handleLiveEvent(payload);
    } catch (err) {
      console.error("Erro parsing SSE event:", err);
    }
  };
}

function handleLiveEvent(event) {
  const { type, timestamp, data } = event;

  if (type === "ACCOUNT_FALLEN") {
    showAlertBanner(data.username, data.reason, data.proxy);
    playAlertBeep();
    appendLogEntry(timestamp, `[ALERTA CRÍTICO // CONTA CAIU] @${data.username} - Motivo: ${data.reason}`, "log-death");
    fetchStatus();
  } else if (type === "ACCOUNT_UPDATE") {
    updateAccountRow(data);
  } else if (type === "ACTION_LIKE") {
    appendLogEntry(timestamp, `[LIKE] @${data.username} curtiu post ${data.post_id} (${data.target || ''})`, "log-like");
    incrementMetric("metric-likes");
  } else if (type === "ACTION_COMMENT") {
    appendLogEntry(timestamp, `[COMENTÁRIO] @${data.username} comentou no feed. Link inserido: ${data.link}`, "log-comment");
    incrementMetric("metric-comments");
  } else if (type === "SYSTEM") {
    appendLogEntry(timestamp, `[SISTEMA] ${data.message}`, "log-system");
  }
}

function showAlertBanner(username, reason, proxy) {
  const banner = document.getElementById("alert-banner");
  const msg = document.getElementById("alert-message");
  msg.innerHTML = `<strong>Atenção:</strong> A conta <strong>@${username}</strong> caiu! Motivo: <em>${reason}</em> (Proxy: ${proxy || 'Nenhum'})`;
  banner.classList.remove("hidden");
}

function dismissAlert() {
  document.getElementById("alert-banner").classList.add("hidden");
}

function appendLogEntry(time, text, cssClass) {
  const terminal = document.getElementById("terminal-body");
  const entry = document.createElement("div");
  entry.className = `log-entry ${cssClass || 'log-system'}`;
  entry.innerHTML = `<span class="log-time">[${time}]</span> ${text}`;
  terminal.appendChild(entry);
  terminal.scrollTop = terminal.scrollHeight;

  const countBadge = document.getElementById("logs-count");
  if (countBadge) countBadge.innerText = terminal.children.length;
}

function clearLogs() {
  document.getElementById("terminal-body").innerHTML = "";
  document.getElementById("logs-count").innerText = "0";
}

async function fetchStatus() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById("metric-total").innerText = data.total_accounts;
    document.getElementById("metric-active").innerText = data.active_accounts;
    document.getElementById("metric-educated").innerText = data.educated_accounts;
    document.getElementById("metric-fallen").innerText = data.fallen_accounts;
    document.getElementById("metric-likes").innerText = data.total_likes;
    document.getElementById("metric-comments").innerText = data.total_comments;

    document.getElementById("accounts-tab-count").innerText = data.total_accounts;

    const fallenCard = document.getElementById("card-fallen-box");
    const fallenSub = document.getElementById("metric-fallen-sub");
    if (data.fallen_accounts > 0) {
      fallenCard.classList.add("has-deaths");
      fallenSub.innerText = `${data.fallen_accounts} conta(s) caíram!`;
    } else {
      fallenCard.classList.remove("has-deaths");
      fallenSub.innerText = "Nenhuma queda detectada";
    }

    const btnStart = document.getElementById("btn-start");
    const btnStop = document.getElementById("btn-stop");
    if (data.is_running) {
      btnStart.classList.add("hidden");
      btnStop.classList.remove("hidden");
    } else {
      btnStart.classList.remove("hidden");
      btnStop.classList.add("hidden");
    }

    renderAccountsTable(data.accounts);
    const liveDot = document.getElementById("live-indicator");
    const connText = document.getElementById("connection-status");
    if (liveDot && connText && !liveDot.classList.contains("connected")) {
      liveDot.classList.add("connected");
      connText.innerText = "STREAM ATIVO";
    }
  } catch (e) {
    const liveDot = document.getElementById("live-indicator");
    const connText = document.getElementById("connection-status");
    if (liveDot && connText) {
      liveDot.classList.remove("connected");
      connText.innerText = "Reconectando...";
    }
  }
}

function incrementMetric(id) {
  const el = document.getElementById(id);
  let val = parseInt(el.innerText || "0", 10);
  el.innerText = val + 1;
}

function renderAccountsTable(accounts) {
  const tbody = document.getElementById("accounts-table-body");
  if (!accounts || accounts.length === 0) {
    tbody.innerHTML = `
      <tr class="empty-row">
        <td colspan="11">
          <div class="empty-state">
            <h3>Nenhuma conta importada ainda</h3>
            <p>Clique em <strong>"Importar (1:1:1)"</strong> para carregar seus Tokens, Proxies e Links.</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  let html = "";
  accounts.forEach(acc => {
    const badgeClass = getBadgeClass(acc.status);
    const badgeLabel = getBadgeLabel(acc.status);

    html += `
      <tr id="row-acc-${acc.id}">
        <td class="cell-mono">${acc.id}</td>
        <td><span class="badge badge-group">${acc.group || "Grupo 1"}</span></td>
        <td><strong>@${acc.username}</strong></td>
        <td><span class="badge ${badgeClass}">${badgeLabel}</span></td>
        <td class="cell-mono">${acc.proxy}</td>
        <td><a href="${acc.assigned_link}" target="_blank" class="cell-link">${acc.assigned_link}</a></td>
        <td style="text-align: center; font-weight: 600;">${acc.followers_count || 0}</td>
        <td style="text-align: center; font-weight: 600;">${acc.education_likes}</td>
        <td style="text-align: center; font-weight: 600;">${acc.comments_count}</td>
        <td style="text-align: center; font-weight: 600; color: var(--accent-red);">${acc.unfollowed_count || 0}</td>
        <td><span style="font-size: 0.85rem; color: var(--text-secondary);">${acc.status_detail}</span></td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}

function updateAccountRow(acc) {
  const row = document.getElementById(`row-acc-${acc.id}`);
  if (!row) {
    fetchStatus();
    return;
  }

  const badgeClass = getBadgeClass(acc.status);
  const badgeLabel = getBadgeLabel(acc.status);

  row.cells[2].innerHTML = `<strong>@${acc.username}</strong>`;
  row.cells[3].innerHTML = `<span class="badge ${badgeClass}">${badgeLabel}</span>`;
  row.cells[6].innerText = acc.followers_count || 0;
  row.cells[7].innerText = acc.education_likes;
  row.cells[8].innerText = acc.comments_count;
  row.cells[9].innerText = acc.unfollowed_count || 0;
  row.cells[10].innerHTML = `<span style="font-size: 0.85rem; color: var(--text-secondary);">${acc.status_detail}</span>`;
}

function getBadgeClass(status) {
  switch (status) {
    case "PENDING": return "badge-pending";
    case "INITIALIZING": return "badge-initializing";
    case "ACTIVE": return "badge-active";
    case "EDUCATING": return "badge-educating";
    case "EDUCATED": return "badge-educated";
    case "COMMENTING": return "badge-commenting";
    case "UNFOLLOWING": return "badge-commenting";
    case "AUTOLIKING": return "badge-commenting";
    case "IDLE": return "badge-idle";
    case "DEAD":
    case "SUSPENDED":
    case "LOCKED": return "badge-fallen";
    default: return "badge-pending";
  }
}

function getBadgeLabel(status) {
  switch (status) {
    case "PENDING": return "Pendente";
    case "INITIALIZING": return "Iniciando";
    case "ACTIVE": return "Online";
    case "EDUCATING": return "Educando";
    case "EDUCATED": return "Educada";
    case "COMMENTING": return "Comentando";
    case "UNFOLLOWING": return "Removendo";
    case "AUTOLIKING": return "Curtindo";
    case "IDLE": return "Parado";
    case "DEAD": return "Token Morto";
    case "SUSPENDED": return "Suspensa";
    case "LOCKED": return "Bloqueada";
    default: return status;
  }
}

// Modal Handlers
function openImportModal() {
  document.getElementById("import-modal").classList.remove("hidden");
}

function closeImportModal() {
  document.getElementById("import-modal").classList.add("hidden");
}

function loadSampleData() {
  document.getElementById("import-tokens").value = 
`a1b2c3d4e5f60718293a4b5c6d7e8f9012345678
b2c3d4e5f60718293a4b5c6d7e8f90123456789a
c3d4e5f60718293a4b5c6d7e8f90123456789ab1`;

  document.getElementById("import-proxies").value = 
`http://user1:pass1@142.250.190.46:8080
http://user2:pass2@142.250.190.47:8080
http://user3:pass3@142.250.190.48:8080`;

  document.getElementById("import-links").value = 
`https://t.me/canal_cripto_vip
https://t.me/sinais_investimentos
https://t.me/comunidade_oficial`;

  document.getElementById("import-comments").value = 
`Muito relevante essa informação! Veja mais detalhes aqui: {link}
Acompanhando o projeto de perto! Acesso direto: {link}
Conteúdo top demais! Dá uma conferida no canal: {link}`;
}

async function submitImport() {
  const tokens = document.getElementById("import-tokens").value.trim();
  const proxies = document.getElementById("import-proxies").value.trim();
  const links = document.getElementById("import-links").value.trim();
  const comments = document.getElementById("import-comments").value.trim();

  if (!tokens) {
    alert("Por favor, insira pelo menos um Auth Token.");
    return;
  }

  try {
    const res = await fetch("/api/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tokens, proxies, links, comments })
    });
    const data = await res.json();
    if (data.success) {
      alert(data.message);
      closeImportModal();
      fetchStatus();
    } else {
      alert("Erro ao importar: " + data.message);
    }
  } catch (e) {
    alert("Falha de conexão com o servidor.");
  }
}

async function applyQuickProxies() {
  const proxies = document.getElementById("quick-proxies").value.trim();
  if (!proxies) {
    alert("Cole pelo menos um proxy antes de aplicar.");
    return;
  }

  try {
    const res = await fetch("/api/proxies", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ proxies })
    });
    const data = await res.json();
    alert(data.message);
    if (data.success) {
      fetchStatus();
    }
  } catch (e) {
    alert("Falha de conexão ao aplicar os proxies.");
  }
}

// Action Triggers
async function startAutomation() {
  try {
    const res = await fetch("/api/start", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      fetchStatus();
    } else {
      alert(data.message);
    }
  } catch (e) {
    alert("Falha ao iniciar automação.");
  }
}

async function stopAutomation() {
  try {
    const res = await fetch("/api/stop", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      fetchStatus();
    }
  } catch (e) {
    alert("Falha ao parar automação.");
  }
}

async function triggerUnfollowNonFollowers() {
  try {
    const res = await fetch("/api/actions/unfollow-non-followers", { method: "POST" });
    const data = await res.json();
    alert(data.message);
    fetchStatus();
  } catch (e) {
    alert("Erro ao disparar remoção de não-seguidores.");
  }
}

function openAutoLikeModal() {
  document.getElementById("autolike-modal").classList.remove("hidden");
}

function closeAutoLikeModal() {
  document.getElementById("autolike-modal").classList.add("hidden");
}

async function submitAutoLikeBatch() {
  const rawKw = document.getElementById("autolike-keywords").value.trim();
  const count = parseInt(document.getElementById("autolike-count").value, 10);
  const keywords = rawKw.split(",").map(k => k.trim()).filter(Boolean);

  try {
    const res = await fetch("/api/actions/auto-like", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keywords, count })
    });
    const data = await res.json();
    alert(data.message);
    closeAutoLikeModal();
    fetchStatus();
  } catch (e) {
    alert("Erro ao ativar curtidor em lote.");
  }
}

function openVideoModal() {
  document.getElementById("video-modal").classList.remove("hidden");
  document.getElementById("video-results").innerHTML = "";
}

function closeVideoModal() {
  document.getElementById("video-modal").classList.add("hidden");
}

async function submitVideoDownload() {
  const url_or_id = document.getElementById("video-tweet-url").value.trim();
  if (!url_or_id) return alert("Cole o link ou ID do tweet.");

  const resultsDiv = document.getElementById("video-results");
  resultsDiv.innerHTML = "<p style='color: var(--accent-cyan);'>Buscando stream MP4 no Twitter...</p>";

  try {
    const res = await fetch("/api/actions/video-download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url_or_id })
    });
    const data = await res.json();
    if (data.success && data.videos.length) {
      let h = "<h4 style='margin-bottom:8px;'>Vídeos Disponíveis:</h4>";
      data.videos.forEach((v, i) => {
        h += `
          <div class="video-link-item">
            <span class="video-bitrate">Stream #${i + 1} (${v.bitrate ? v.bitrate + ' bps' : 'Alta Res'})</span>
            <a href="${v.url}" target="_blank" download class="btn btn-primary btn-sm">Baixar MP4 ⬇</a>
          </div>
        `;
      });
      resultsDiv.innerHTML = h;
    } else {
      resultsDiv.innerHTML = `<p style='color: var(--accent-red);'>${data.message || 'Nenhum vídeo encontrado.'}</p>`;
    }
  } catch (e) {
    resultsDiv.innerHTML = "<p style='color: var(--accent-red);'>Falha na extração do vídeo.</p>";
  }
}

function exportData(format) {
  window.open(`/api/export/${format}`, "_blank");
}

async function saveSettings() {
  const minEdu = parseInt(document.getElementById("cfg-min-edu").value, 10);
  const maxEdu = parseInt(document.getElementById("cfg-max-edu").value, 10);
  const probMin = parseFloat(document.getElementById("cfg-prob-min").value) / 100.0;
  const probMax = parseFloat(document.getElementById("cfg-prob-max").value) / 100.0;
  const delayMin = parseFloat(document.getElementById("cfg-delay-min").value);
  const delayMax = parseFloat(document.getElementById("cfg-delay-max").value);

  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        min_education_likes: minEdu,
        max_education_likes: maxEdu,
        like_probability_min: probMin,
        like_probability_max: probMax,
        min_action_delay: delayMin,
        max_action_delay: delayMax
      })
    });
    const data = await res.json();
    if (data.success) {
      alert("Configurações salvas com sucesso!");
    }
  } catch (e) {
    alert("Erro ao salvar configurações.");
  }
}

// Conecta System browser tool scripts
const TOOL_SCRIPTS = {
  unfollowNonFollowers: `// Conecta System: Unfollow Non-Followers
(() => {
  const $followButtons = '[data-testid$="-unfollow"]';
  const $confirmButton = '[data-testid="confirmationSheetConfirm"]';
  const retry = { count: 0, limit: 3 };
  const sleep = (s) => new Promise(r => setTimeout(r, s * 1000));
  const unfollowAll = async (buttons) => {
    console.log(\`UNFOLLOWING \${buttons.length} USERS...\`);
    for (const btn of buttons) {
      btn.click();
      await sleep(1);
      document.querySelector($confirmButton)?.click();
      await sleep(1);
    }
  };
  const nextBatch = async () => {
    window.scrollTo(0, document.body.scrollHeight);
    await sleep(2);
    let buttons = Array.from(document.querySelectorAll($followButtons));
    buttons = buttons.filter(b => b.parentElement?.parentElement?.querySelector('[data-testid="userFollowIndicator"]') === null);
    if (buttons.length > 0) {
      await unfollowAll(buttons);
      await sleep(2);
      return nextBatch();
    } else if (retry.count < retry.limit) {
      retry.count++;
      await sleep(2);
      return nextBatch();
    } else {
      console.log('CONCLUÍDO! Todos os que não te seguiam foram removidos.');
    }
  };
  nextBatch();
})();`,

  unfollowEveryone: `// Conecta System: Unfollow Everyone
(() => {
  const $followButtons = '[data-testid$="-unfollow"]';
  const $confirmButton = '[data-testid="confirmationSheetConfirm"]';
  const sleep = (s) => new Promise(r => setTimeout(r, s * 1000));
  const nextBatch = async () => {
    window.scrollTo(0, document.body.scrollHeight);
    await sleep(1);
    const buttons = Array.from(document.querySelectorAll($followButtons));
    if (buttons.length > 0) {
      for (const btn of buttons) {
        btn.click();
        await sleep(0.8);
        document.querySelector($confirmButton)?.click();
        await sleep(0.8);
      }
      return nextBatch();
    }
    console.log('CONCLUÍDO! Deixou de seguir todos.');
  };
  nextBatch();
})();`,

  autoLiker: `// Conecta System: Auto Liker by Keywords
(() => {
  const OPTIONS = {
    KEYWORDS: ['telegram', 'crypto', 'web3', 'ai'],
    MAX_LIKES: 25,
    MIN_DELAY: 2000,
    MAX_DELAY: 4500
  };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  let count = 0;
  const process = async () => {
    for (const tweet of document.querySelectorAll('[data-testid="tweet"]')) {
      if (count >= OPTIONS.MAX_LIKES) {
        console.log(\`CONCLUÍDO! \${count} tweets curtidos.\`);
        return;
      }
      const text = tweet.querySelector('[data-testid="tweetText"]')?.textContent || '';
      const matches = !OPTIONS.KEYWORDS.length || OPTIONS.KEYWORDS.some(k => text.toLowerCase().includes(k.toLowerCase()));
      const likeBtn = tweet.querySelector('[data-testid="like"]');
      if (matches && likeBtn) {
        likeBtn.click();
        count++;
        console.log(\`Curtido (\${count}): "\${text.substring(0, 40)}..."\`);
        await sleep(OPTIONS.MIN_DELAY + Math.random() * (OPTIONS.MAX_DELAY - OPTIONS.MIN_DELAY));
      }
    }
    window.scrollBy(0, 800);
    await sleep(2000);
    process();
  };
  process();
})();`,

  followEngagers: `// Conecta System: Follow Engagers
(() => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  let count = 0;
  const run = async () => {
    for (const cell of document.querySelectorAll('[data-testid="UserCell"]')) {
      if (count >= 20) return console.log('Finalizado!');
      const btn = cell.querySelector('[data-testid$="-follow"]');
      if (btn) {
        btn.click();
        count++;
        console.log(\`Seguiu #\${count}\`);
        await sleep(2500);
      }
    }
    window.scrollBy(0, 500);
    await sleep(2000);
    run();
  };
  run();
})();`,

  videoDownloader: `// Conecta System: Video Downloader
(() => {
  const html = document.documentElement.innerHTML;
  const matches = html.match(/https:\\/\\/video\\.twimg\\.com\\/[^"\'\\s]+\\.mp4[^"\'\\s]*/g) || [];
  const cleanUrls = Array.from(new Set(matches.map(u => u.replace(/\\\\u002F/g, '/').replace(/\\\\/g, '').split('"')[0].split("'")[0])));
  if (!cleanUrls.length) return alert('Nenhum vídeo MP4 encontrado nesta página!');
  const bestUrl = cleanUrls[0];
  const a = document.createElement('a');
  a.href = bestUrl;
  a.download = \`twitter-video-\${Date.now()}.mp4\`;
  a.target = '_blank';
  a.click();
})();`,

  leaveCommunities: `// Conecta System: Leave All Communities
(() => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const run = async () => {
    const joined = document.querySelector('button[aria-label^="Joined"]');
    if (joined) {
      joined.click();
      await sleep(1000);
      document.querySelector('[data-testid="confirmationSheetConfirm"]')?.click();
      await sleep(1500);
      document.querySelector('a[aria-label="Communities"]')?.click();
      await sleep(2500);
      return run();
    }
    const link = document.querySelector('a[href^="/i/communities/"]');
    if (link) {
      link.click();
      await sleep(2500);
      return run();
    }
    console.log('Todas as comunidades foram abandonadas.');
  };
  run();
})();`
};

function copyToolScript(key) {
  const code = TOOL_SCRIPTS[key];
  if (!code) return;
  navigator.clipboard.writeText(code).then(() => {
    alert("Código copiado para a área de transferência! Cole no Console (F12) do Twitter/X.");
  }).catch(() => {
    prompt("Copie o código abaixo:", code);
  });
}
