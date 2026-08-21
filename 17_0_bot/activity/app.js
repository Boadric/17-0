/**
 * 17-0 NFL Draft & Chemistry Strategy Game — Virtual Tabletop Client
 */

// Application State
const state = {
  round: 1,
  totalRounds: 7,
  team: 'KC',
  season: 2020,
  teamName: 'Kansas City Chiefs',
  color: '#E31837',
  emoji: '🏹',
  availablePlayers: [],
  positionFilter: 'ALL',
  searchQuery: '',
  teamRerollsLeft: 1,
  seasonRerollsLeft: 1,
  roster: {
    QB: null,
    RB1: null,
    RB2: null,
    WR1: null,
    WR2: null,
    TE: null,
    FLX: null,
  },
  breakdown: {
    base_fppg: 0,
    chemistry_fppg: 0,
    total_score: 0,
    projected_record: '0-0',
    tier_badge: '🎟️',
    tier_name: 'Lottery Bound',
    active_links: [],
  },
  user: {
    id: 'user_' + Math.random().toString(36).substr(2, 8),
    username: 'GridironGM',
    avatar: null,
  },
};

// DOM Elements
const el = {
  currentRound: document.getElementById('current-round'),
  rollBanner: document.getElementById('roll-banner'),
  rollEmoji: document.getElementById('roll-emoji'),
  rollTeamCode: document.getElementById('roll-team-code'),
  rollSeason: document.getElementById('roll-season'),
  rollTeamName: document.getElementById('roll-team-name'),
  teamRerollsLeft: document.getElementById('team-rerolls-left'),
  seasonRerollsLeft: document.getElementById('season-rerolls-left'),
  rerollTeamBtn: document.getElementById('reroll-team-btn'),
  rerollSeasonBtn: document.getElementById('reroll-season-btn'),
  searchInput: document.getElementById('search-input'),
  clearSearch: document.getElementById('clear-search'),
  playerCardPack: document.getElementById('player-card-pack'),
  eligibleHint: document.getElementById('eligible-positions-hint'),
  filterTabs: document.querySelectorAll('.filter-tab'),
  chemistryFeed: document.getElementById('chemistry-feed'),
  activeChemCount: document.getElementById('active-chem-count'),
  hudTierBadge: document.getElementById('hud-tier-badge'),
  hudRecord: document.getElementById('hud-record'),
  hudTotalScore: document.getElementById('hud-total-score'),
  gameOverModal: document.getElementById('game-over-modal'),
  leaderboardModal: document.getElementById('leaderboard-modal'),
  rulesModal: document.getElementById('rules-modal'),
  soundBtn: document.getElementById('sound-btn'),
};

// Helper: Auto-slot assignment logic
function autoAssignSlot(position) {
  const pos = position.toUpperCase();
  if (pos === 'QB') {
    return state.roster.QB === null ? 'QB' : null;
  } else if (pos === 'RB') {
    if (state.roster.RB1 === null) return 'RB1';
    if (state.roster.RB2 === null) return 'RB2';
    if (state.roster.FLX === null) return 'FLX';
    return null;
  } else if (pos === 'WR') {
    if (state.roster.WR1 === null) return 'WR1';
    if (state.roster.WR2 === null) return 'WR2';
    if (state.roster.FLX === null) return 'FLX';
    return null;
  } else if (pos === 'TE') {
    if (state.roster.TE === null) return 'TE';
    if (state.roster.FLX === null) return 'FLX';
    return null;
  }
  return null;
}

function getEligiblePositions() {
  const positions = ['QB', 'RB', 'WR', 'TE'];
  return positions.filter((p) => autoAssignSlot(p) !== null);
}

// Fetch Initial Roll from API
async function fetchRoll() {
  try {
    const res = await fetch('/api/roll');
    const data = await res.json();
    state.team = data.team;
    state.season = data.season;
    state.teamName = data.team_name;
    state.color = data.color;
    state.emoji = data.emoji;
    state.availablePlayers = data.players || [];
    renderRollCard();
    renderDraftPack();
    updateFilterTabs();
  } catch (err) {
    console.error('Error fetching roll:', err);
  }
}

// Reroll Team
async function rerollTeam() {
  if (state.teamRerollsLeft <= 0) return;
  window.soundEngine.playReroll();
  state.teamRerollsLeft -= 1;
  el.teamRerollsLeft.textContent = state.teamRerollsLeft;
  el.rerollTeamBtn.disabled = state.teamRerollsLeft <= 0;

  try {
    const res = await fetch('/api/reroll-team', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        season: state.season,
        current_team: state.team,
        positions: getEligiblePositions(),
      }),
    });
    const data = await res.json();
    state.team = data.team;
    state.teamName = data.team_name;
    state.color = data.color;
    state.emoji = data.emoji;
    state.availablePlayers = data.players || [];
    renderRollCard();
    renderDraftPack();
  } catch (err) {
    console.error('Error rerolling team:', err);
  }
}

// Reroll Season
async function rerollSeason() {
  if (state.seasonRerollsLeft <= 0) return;
  window.soundEngine.playReroll();
  state.seasonRerollsLeft -= 1;
  el.seasonRerollsLeft.textContent = state.seasonRerollsLeft;
  el.rerollSeasonBtn.disabled = state.seasonRerollsLeft <= 0;

  try {
    const res = await fetch('/api/reroll-season', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        team: state.team,
        current_season: state.season,
        positions: getEligiblePositions(),
      }),
    });
    const data = await res.json();
    state.season = data.season;
    state.teamName = data.team_name;
    state.availablePlayers = data.players || [];
    renderRollCard();
    renderDraftPack();
  } catch (err) {
    console.error('Error rerolling season:', err);
  }
}

// Draft Player
async function draftPlayer(player) {
  const slot = autoAssignSlot(player.position);
  if (!slot) {
    alert(`All eligible roster slots for ${player.position} are filled!`);
    return;
  }

  window.soundEngine.playDraft();

  // Assign player to roster
  state.roster[slot] = {
    player_id: player.player_id,
    name: player.name,
    position: player.position,
    slot: slot,
    drafted_team: state.team,
    drafted_season: state.season,
    base_fppg: parseFloat(player.ppr_fppg || 0),
    college: player.college,
    draft_year: player.draft_year,
    headshot_url: player.headshot_url || null,
    espn_id: player.espn_id || null,
  };

  // Recalculate score via API
  await recalculateScore();

  // Check if chemistry bonus was triggered
  if (state.breakdown.active_links.length > 0) {
    window.soundEngine.playChemistry();
  }

  renderTabletopCards();

  // Check game over
  const draftedCount = Object.values(state.roster).filter(Boolean).length;
  if (draftedCount >= state.totalRounds) {
    showGameOverModal();
    return;
  }

  // Advance to next round
  state.round += 1;
  el.currentRound.textContent = state.round;
  state.positionFilter = 'ALL';
  state.searchQuery = '';
  el.searchInput.value = '';
  el.clearSearch.style.display = 'none';

  await fetchRoll();
}

// Recalculate Score
async function recalculateScore() {
  try {
    const res = await fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ roster: state.roster }),
    });
    const data = await res.json();
    state.breakdown = data;

    // Update roster with latest applied bonuses
    if (data.roster) {
      Object.keys(data.roster).forEach((slot) => {
        if (state.roster[slot] && data.roster[slot]) {
          state.roster[slot].applied_bonuses = data.roster[slot].applied_bonuses || [];
        }
      });
    }

    renderScoreStats();
  } catch (err) {
    console.error('Error calculating score:', err);
  }
}

// Render Roll Card Banner
function renderRollCard() {
  el.rollEmoji.textContent = state.emoji;
  el.rollTeamCode.textContent = state.team;
  el.rollSeason.textContent = state.season;
  el.rollTeamName.textContent = state.teamName;
  el.rollBanner.style.borderColor = state.color || '#1e293b';
}

// Render Virtual Tabletop Trading Cards (The 7 Board Slots)
function renderTabletopCards() {
  const slots = ['WR1', 'QB', 'WR2', 'TE', 'RB1', 'RB2', 'FLX'];

  slots.forEach((slot) => {
    const slotContainer = document.getElementById(`slot-${slot}`);
    if (!slotContainer) return;

    const p = state.roster[slot];

    if (p) {
      const hasChem = p.applied_bonuses && p.applied_bonuses.length > 0;
      const chemText = hasChem ? p.applied_bonuses.join(' · ') : '';
      const college = p.college || 'N/A';
      const draftYear = p.draft_year ? `'${String(p.draft_year).slice(2)} Draft` : 'UDFA';

      // Headshot URL with fallback
      const photoSrc = p.headshot_url || (p.espn_id ? `https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/${p.espn_id}.png&w=350&h=254` : '');

      slotContainer.innerHTML = `
        <div class="trading-card ${hasChem ? 'chemistry-active' : ''}">
          <div class="card-header-bar">
            <span class="card-slot-tag slot-pos-badge ${p.position.toLowerCase()}">${slot}</span>
            <span class="card-team-tag">${p.drafted_season} ${p.drafted_team}</span>
          </div>
          <div class="card-photo-wrap">
            ${photoSrc ? `<img src="${photoSrc}" class="card-headshot-img" alt="${p.name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">` : ''}
            <div class="card-fallback-avatar" style="${photoSrc ? 'display:none;' : 'display:block;'}">🏈</div>
          </div>
          <div class="card-info-wrap">
            <div class="card-player-name">${p.name}</div>
            <div class="card-meta-line">${college} · ${draftYear}</div>
            ${hasChem ? `<div class="card-chem-bonuses">⚡ ${chemText}</div>` : ''}
            <div class="card-fppg-badge">
              <span class="card-fppg-val">${p.base_fppg.toFixed(1)}</span>
              <span class="card-fppg-lbl">FPPG</span>
            </div>
          </div>
        </div>
      `;
    } else {
      // Empty placeholder
      const posClass = slot.startsWith('WR') ? 'wr' : slot.startsWith('RB') ? 'rb' : slot.toLowerCase();
      const hint = slot === 'FLX' ? 'RB / WR / TE' : 'Open Slot';
      slotContainer.innerHTML = `
        <div class="slot-placeholder">
          <span class="slot-pos-badge ${posClass}">${slot}</span>
          <span class="slot-add-icon">+</span>
          <span class="slot-hint">${hint}</span>
        </div>
      `;
    }
  });

  // Render Chemistry Links Feed
  el.chemistryFeed.innerHTML = '';
  const links = state.breakdown.active_links || [];
  el.activeChemCount.textContent = `${links.length} Links Active`;

  if (links.length > 0) {
    links.forEach((l) => {
      const pill = document.createElement('div');
      pill.className = 'chem-link-pill';
      pill.innerHTML = `⚡ <strong>${l.player1_name}</strong> & <strong>${l.player2_name}</strong>: ${l.description} (+${l.team_bonus.toFixed(0)} Team)`;
      el.chemistryFeed.appendChild(pill);
    });
  }
}

// Render Available Weapons Pack
function renderDraftPack() {
  const eligible = getEligiblePositions();
  let filtered = state.availablePlayers;

  // Filter by position tab
  if (state.positionFilter !== 'ALL') {
    filtered = filtered.filter((p) => p.position.toUpperCase() === state.positionFilter);
  } else {
    filtered = filtered.filter((p) => eligible.includes(p.position.toUpperCase()));
  }

  // Filter by search query
  if (state.searchQuery.trim()) {
    const q = state.searchQuery.toLowerCase();
    filtered = filtered.filter((p) => p.name.toLowerCase().includes(q));
  }

  el.playerCardPack.innerHTML = '';

  if (filtered.length === 0) {
    el.playerCardPack.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 20px; color: #64748b;">
        <span>❌ No available players found for your open slots.</span><br>
        <span>Try rerolling the team or year!</span>
      </div>
    `;
    return;
  }

  filtered.forEach((p) => {
    const card = document.createElement('div');
    const isDrafted = Object.values(state.roster).some((dp) => dp && dp.player_id === p.player_id);

    card.className = `draft-card ${isDrafted ? 'drafted' : ''}`;

    const pos = p.position.toUpperCase();
    const posClass = pos.toLowerCase();
    const fppg = parseFloat(p.ppr_fppg || 0).toFixed(1);
    const college = p.college || 'N/A';
    const draftYear = p.draft_year ? `'${String(p.draft_year).slice(2)}` : 'UDFA';

    const photoSrc = p.headshot_url || (p.espn_id ? `https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/${p.espn_id}.png&w=350&h=254` : '');

    card.innerHTML = `
      <div class="card-header-bar">
        <span class="slot-pos-badge ${posClass}">${pos}</span>
        <span class="card-team-tag">${state.team}</span>
      </div>
      <div class="card-photo-wrap">
        ${photoSrc ? `<img src="${photoSrc}" class="card-headshot-img" alt="${p.name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">` : ''}
        <div class="card-fallback-avatar" style="${photoSrc ? 'display:none;' : 'display:block;'}">🏈</div>
      </div>
      <div class="card-info-wrap">
        <div class="card-player-name">${p.name} ${isDrafted ? '*(Drafted)*' : ''}</div>
        <div class="card-meta-line">${college} · ${draftYear}</div>
        <div class="card-fppg-badge">
          <span class="card-fppg-val">${fppg}</span>
          <span class="card-fppg-lbl">FPPG</span>
        </div>
      </div>
    `;

    if (!isDrafted) {
      card.onclick = () => draftPlayer(p);
    }

    el.playerCardPack.appendChild(card);
  });
}

// Update Filter Tabs state
function updateFilterTabs() {
  const eligible = getEligiblePositions();

  el.filterTabs.forEach((tab) => {
    const pos = tab.dataset.pos;
    if (pos === 'ALL') {
      tab.classList.toggle('active', state.positionFilter === 'ALL');
    } else {
      const isEligible = eligible.includes(pos);
      tab.disabled = !isEligible;
      tab.classList.toggle('active', state.positionFilter === pos);
    }
  });

  el.eligibleHint.textContent = `Eligible: ${eligible.join(', ')}`;
}

// Render Score Stats
function renderScoreStats() {
  const b = state.breakdown;
  el.hudTierBadge.textContent = b.tier_badge;
  el.hudRecord.textContent = b.projected_record;
  el.hudTotalScore.textContent = `${b.total_score.toFixed(1)} FPPG`;
}

// Show Game Over Victory Modal
function showGameOverModal() {
  const b = state.breakdown;
  window.soundEngine.playVictory();

  if (window.confetti) {
    window.confetti({
      particleCount: 150,
      spread: 90,
      origin: { y: 0.6 },
    });
  }

  document.getElementById('modal-badge').textContent = b.tier_badge;
  document.getElementById('modal-record').textContent = b.projected_record;
  document.getElementById('modal-tier-tag').textContent = b.tier_name;
  document.getElementById('modal-base').textContent = b.base_fppg.toFixed(1);
  document.getElementById('modal-chem').textContent = `+${b.chemistry_fppg.toFixed(1)}`;
  document.getElementById('modal-total').textContent = `${b.total_score.toFixed(1)} FPPG`;

  // Roster Recap
  const modalRosterList = document.getElementById('modal-roster-list');
  modalRosterList.innerHTML = '';
  Object.entries(state.roster).forEach(([slot, p]) => {
    if (!p) return;
    const item = document.createElement('div');
    item.className = 'lb-row';
    item.innerHTML = `
      <span><strong>${slot}</strong>: ${p.name} (${p.drafted_season} ${p.drafted_team})</span>
      <span class="lb-score">${p.base_fppg.toFixed(1)} FPPG</span>
    `;
    modalRosterList.appendChild(item);
  });

  // Chemistry Links Recap
  const modalLinksList = document.getElementById('modal-links-list');
  modalLinksList.innerHTML = '';
  if (b.active_links && b.active_links.length > 0) {
    b.active_links.forEach((l) => {
      const pill = document.createElement('div');
      pill.className = 'chem-link-pill';
      pill.innerHTML = `⚡ <strong>${l.player1_name}</strong> & <strong>${l.player2_name}</strong>: ${l.description} (+${l.team_bonus.toFixed(0)})`;
      modalLinksList.appendChild(pill);
    });
  } else {
    modalLinksList.innerHTML = '<span class="card-meta-line">No active chemistry bonuses triggered.</span>';
  }

  el.gameOverModal.style.display = 'flex';
}

// Save Game to Leaderboard
async function saveGameToLeaderboard() {
  const btn = document.getElementById('save-leaderboard-btn');
  btn.disabled = true;
  btn.textContent = 'Saving...';

  try {
    const res = await fetch('/api/leaderboard/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: state.user.id,
        username: state.user.username,
        roster: state.roster,
      }),
    });
    const data = await res.json();
    if (data.success) {
      btn.textContent = 'Saved to Hall of Fame! ✅';
    }
  } catch (err) {
    console.error('Error saving leaderboard:', err);
    btn.disabled = false;
    btn.textContent = 'Retry Save';
  }
}

// Show Leaderboard Modal
async function showLeaderboardModal() {
  window.soundEngine.playClick();
  el.leaderboardModal.style.display = 'flex';
  const listEl = document.getElementById('leaderboard-list');
  listEl.innerHTML = '<div class="loading-spinner">Loading Hall of Fame...</div>';

  try {
    const res = await fetch('/api/leaderboard');
    const data = await res.json();
    const entries = data.leaderboard || [];

    if (entries.length === 0) {
      listEl.innerHTML = '<div class="empty-state">No games recorded yet! Play a game to enter the Hall of Fame.</div>';
      return;
    }

    listEl.innerHTML = '';
    entries.forEach((e, idx) => {
      const medal = idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : `#${idx + 1}`;
      const row = document.createElement('div');
      row.className = 'lb-row';
      row.innerHTML = `
        <div class="lb-rank-user">
          <span class="lb-rank">${medal}</span>
          <span class="lb-username">${e.username}</span>
        </div>
        <div class="lb-score-record">
          <div class="lb-score">${parseFloat(e.total_score).toFixed(1)} FPPG</div>
          <div class="lb-record">${e.projected_record}</div>
        </div>
      `;
      listEl.appendChild(row);
    });
  } catch (err) {
    console.error('Error loading leaderboard:', err);
    listEl.innerHTML = '<div class="empty-state">Failed to load leaderboard.</div>';
  }
}

// Reset Game
function resetGame() {
  window.soundEngine.playClick();
  state.round = 1;
  state.teamRerollsLeft = 1;
  state.seasonRerollsLeft = 1;
  state.roster = { QB: null, RB1: null, RB2: null, WR1: null, WR2: null, TE: null, FLX: null };
  state.breakdown = {
    base_fppg: 0,
    chemistry_fppg: 0,
    total_score: 0,
    projected_record: '0-0',
    tier_badge: '🎟️',
    tier_name: 'Lottery Bound',
    active_links: [],
  };
  state.positionFilter = 'ALL';
  state.searchQuery = '';

  el.currentRound.textContent = 1;
  el.teamRerollsLeft.textContent = 1;
  el.seasonRerollsLeft.textContent = 1;
  el.rerollTeamBtn.disabled = false;
  el.rerollSeasonBtn.disabled = false;
  el.gameOverModal.style.display = 'none';

  fetchRoll();
  renderTabletopCards();
  renderScoreStats();
}

// Event Listeners
function setupEvents() {
  // Filter Tabs
  el.filterTabs.forEach((tab) => {
    tab.onclick = () => {
      state.positionFilter = tab.dataset.pos;
      updateFilterTabs();
      renderDraftPack();
      window.soundEngine.playClick();
    };
  });

  // Rerolls
  el.rerollTeamBtn.onclick = rerollTeam;
  el.rerollSeasonBtn.onclick = rerollSeason;

  // Search
  el.searchInput.oninput = (e) => {
    state.searchQuery = e.target.value;
    el.clearSearch.style.display = state.searchQuery ? 'block' : 'none';
    renderDraftPack();
  };

  el.clearSearch.onclick = () => {
    state.searchQuery = '';
    el.searchInput.value = '';
    el.clearSearch.style.display = 'none';
    renderDraftPack();
  };

  // Modals & Navigation
  el.soundBtn.onclick = () => {
    const isEnabled = window.soundEngine.toggle();
    el.soundBtn.textContent = isEnabled ? '🔊' : '🔇';
  };

  document.getElementById('rules-btn').onclick = () => {
    window.soundEngine.playClick();
    el.rulesModal.style.display = 'flex';
  };

  document.getElementById('close-rules').onclick = () => {
    el.rulesModal.style.display = 'none';
  };

  document.getElementById('leaderboard-btn').onclick = showLeaderboardModal;
  document.getElementById('close-leaderboard').onclick = () => {
    el.leaderboardModal.style.display = 'none';
  };

  document.getElementById('restart-btn').onclick = resetGame;
  document.getElementById('play-again-btn').onclick = resetGame;
  document.getElementById('save-leaderboard-btn').onclick = saveGameToLeaderboard;
}

// Initialize Discord Embedded App SDK (if in Discord Activity)
async function initDiscordSdk() {
  if (window.DiscordSDK) {
    try {
      const discordSdk = new window.DiscordSDK.DiscordSDK('1540222119697322004');
      await discordSdk.ready();
      console.log('Discord SDK initialized successfully!');
      if (discordSdk.user) {
        state.user.id = discordSdk.user.id;
        state.user.username = discordSdk.user.username;
      }
    } catch (e) {
      console.log('Running in browser mode.');
    }
  }
}

// App Bootstrap
window.addEventListener('DOMContentLoaded', async () => {
  setupEvents();
  await initDiscordSdk();
  await fetchRoll();
  renderTabletopCards();
});
