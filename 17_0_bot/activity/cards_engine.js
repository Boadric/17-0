/**
 * 17-0 Cards Engine: 3D Horizontal Fan Arc Math, Tiers, Shaders & Inspect Modal
 */

const HISTORIC_SUPERSTARS = [
  'tom brady', 'patrick mahomes', 'randy moss', 'peyton manning', 
  'rob gronkowski', 'ladainian tomlinson', 'jerry rice', 'calvin johnson', 
  'adrian peterson', 'drew brees', 'aaron rodgers', 'marshawn lynch',
  'travis kelce', 'antonio brown', 'larry fitzgerald', 'derrick henry',
  'julio jones', 'christian mccaffrey', 'justin jefferson', 'tyreek hill',
  'cooper kupp', 'lamar jackson', 'cam newton', 'russell wilson'
];

class CardsEngine {
  // Determine card tier based on FPPG rating and superstar status
  static getCardTier(player) {
    const nameLower = (player.name || '').toLowerCase();
    const fppg = parseFloat(player.ppr_fppg || player.base_fppg || 0);

    const isSuperstar = HISTORIC_SUPERSTARS.some((s) => nameLower.includes(s));
    if (isSuperstar && fppg >= 14) {
      return {
        id: 'superstar',
        name: 'Historic Superstar',
        badge: '✨ SUPERSTAR',
        color: '#fbbf24',
        border: 'superstar-hologram',
        glow: 'rgba(251, 191, 36, 0.9)',
      };
    }

    if (fppg >= 18) {
      return {
        id: 'legendary',
        name: 'Legendary Gold',
        badge: '👑 LEGENDARY',
        color: '#f59e0b',
        border: 'tier-legendary',
        glow: 'rgba(245, 158, 11, 0.8)',
      };
    } else if (fppg >= 14) {
      return {
        id: 'epic',
        name: 'Epic Purple',
        badge: '🟣 EPIC',
        color: '#a855f7',
        border: 'tier-epic',
        glow: 'rgba(168, 85, 247, 0.7)',
      };
    } else if (fppg >= 10) {
      return {
        id: 'rare',
        name: 'Rare Blue',
        badge: '🔵 RARE',
        color: '#0ea5e9',
        border: 'tier-rare',
        glow: 'rgba(14, 165, 233, 0.6)',
      };
    }

    return {
      id: 'silver',
      name: 'Silver Common',
      badge: '🥈 SILVER',
      color: '#94a3b8',
      border: 'tier-silver',
      glow: 'rgba(148, 163, 184, 0.4)',
    };
  }

  // Calculate 3D Horizontal Fan Arc Transform for cards spread across the table
  static calculateFanTransform(totalCards, currentIndex, containerWidth) {
    if (totalCards <= 1) {
      return { translateX: 0, translateY: 0, rotation: 0, zIndex: 10 };
    }

    const mid = (totalCards - 1) / 2;
    const offset = currentIndex - mid; // e.g. for 5 cards: -2, -1, 0, 1, 2

    // Dynamic horizontal spread based on the actual measured container width
    const validWidth = Math.max(300, containerWidth || window.innerWidth || 800);
    // Scales dynamically from docked 360px sidebar up to 4K widescreen desktop
    const cardSpacing = Math.min(180, Math.max(48, (validWidth * 0.76) / totalCards));
    const translateX = offset * cardSpacing;

    // Gentle parabolic curve dip
    const translateY = Math.pow(Math.abs(offset), 1.5) * 6;

    // Smooth rotational arc from -22deg to +22deg
    const maxRot = Math.min(26, totalCards * 4.5);
    const rotation = (offset / (mid || 1)) * (maxRot / 2);

    // Center cards on top
    const zIndex = 10 + Math.round(10 - Math.abs(offset));

    return {
      translateX: Math.round(translateX),
      translateY: Math.round(translateY),
      rotation: Math.round(rotation * 10) / 10,
      zIndex: zIndex,
    };
  }

  // Attach 3D physics tilt & glare tracking to a card element
  static attach3DTilt(cardElement, baseTransform) {
    if (!cardElement) return;

    const handleMove = (e) => {
      const rect = cardElement.getBoundingClientRect();
      const clientX = e.clientX || (e.touches && e.touches[0] ? e.touches[0].clientX : rect.left + rect.width / 2);
      const clientY = e.clientY || (e.touches && e.touches[0] ? e.touches[0].clientY : rect.top + rect.height / 2);

      const x = clientX - rect.left;
      const y = clientY - rect.top;

      const normX = (x / rect.width - 0.5) * 2;
      const normY = (y / rect.height - 0.5) * 2;

      const tiltX = normY * -12;
      const tiltY = normX * 12;

      // Lift from fan arc and apply tilt
      cardElement.style.transform = `translate3d(${baseTransform.translateX}px, ${baseTransform.translateY - 32}px, 60px) rotate(${baseTransform.rotation + tiltY * 0.3}deg) rotateX(${tiltX}deg) rotateY(${tiltY}deg) scale(1.18)`;
      cardElement.style.zIndex = '100';

      const glare = cardElement.querySelector('.card-glare-layer');
      if (glare) {
        glare.style.opacity = '1';
        glare.style.background = `radial-gradient(circle at ${x}px ${y}px, rgba(255,255,255,0.45) 0%, rgba(255,255,255,0.08) 50%, transparent 70%)`;
      }
    };

    const handleLeave = () => {
      cardElement.style.transform = `translate3d(${baseTransform.translateX}px, ${baseTransform.translateY}px, 0px) rotate(${baseTransform.rotation}deg) scale(1)`;
      cardElement.style.zIndex = `${baseTransform.zIndex}`;

      const glare = cardElement.querySelector('.card-glare-layer');
      if (glare) {
        glare.style.opacity = '0';
      }
    };

    cardElement.addEventListener('mousemove', handleMove);
    cardElement.addEventListener('mouseleave', handleLeave);
    cardElement.addEventListener('touchmove', handleMove, { passive: true });
    cardElement.addEventListener('touchend', handleLeave);
  }

  // Render HTML for a complete 3D Trading Card
  static createCardHTML(player, options = {}) {
    const tier = this.getCardTier(player);
    const fppg = parseFloat(player.ppr_fppg || player.base_fppg || 0).toFixed(1);
    const pos = (player.position || 'FLX').toUpperCase();
    const college = player.college || 'N/A';
    const draftYear = player.draft_year ? `'${String(player.draft_year).slice(2)}` : 'UDFA';
    const isSuperstar = tier.id === 'superstar';
    const photoUrl = options.photoUrl || '';
    const team = player.team || player.drafted_team || 'NFL';
    const season = player.season || player.drafted_season || '';

    return `
      <div class="card-inner ${tier.border} ${isSuperstar ? 'superstar-hologram' : ''}">
        <!-- Holographic Sheen & Glare Overlay -->
        <div class="card-glare-layer"></div>
        <div class="card-foil-sheen"></div>

        <!-- Card Top Bar: Position Shield & Tier Ribbon -->
        <div class="card-top-bar">
          <div class="pos-shield pos-${pos.toLowerCase()}">${pos}</div>
          <div class="tier-pill tier-${tier.id}">${tier.badge}</div>
          <div class="team-tag">${season} ${team}</div>
        </div>

        <!-- Card Headshot Photo Frame -->
        <div class="card-portrait-wrap">
          ${photoUrl ? `<img src="${photoUrl}" class="portrait-img" alt="${player.name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">` : ''}
          <div class="portrait-fallback" style="${photoUrl ? 'display:none;' : 'display:flex;'}">🏈</div>
        </div>

        <!-- Card Metadata & Stats Footer -->
        <div class="card-bottom-plate">
          <div class="player-name-row">
            <span class="player-name">${player.name}</span>
            <button class="inspect-btn" title="Inspect Player Stats" onclick="event.stopPropagation(); window.CardsEngine.openInspectModal('${encodeURIComponent(JSON.stringify(player))}');">ℹ️</button>
          </div>
          <div class="player-subline">${college} · ${draftYear}</div>
          <div class="rating-strip">
            <span class="rating-label">PPR FPPG</span>
            <span class="rating-value tier-text-${tier.id}">${fppg}</span>
          </div>
        </div>
      </div>
    `;
  }

  // Open Full-Screen Inspect Card Modal
  static openInspectModal(playerJsonStr) {
    try {
      const p = JSON.parse(decodeURIComponent(playerJsonStr));
      const tier = this.getCardTier(p);
      const fppg = parseFloat(p.ppr_fppg || p.base_fppg || 0).toFixed(1);
      const modal = document.getElementById('inspect-card-modal');
      if (!modal) return;

      const photoUrl = p.headshot_url ? `/api/image-proxy?url=${encodeURIComponent(p.headshot_url)}` : '';

      document.getElementById('inspect-title').textContent = p.name;
      document.getElementById('inspect-tier').textContent = tier.name;
      document.getElementById('inspect-tier').className = `inspect-tier-tag tier-text-${tier.id}`;
      document.getElementById('inspect-team-season').textContent = `${p.season || p.drafted_season || ''} ${p.team || p.drafted_team || ''} · ${p.position}`;
      document.getElementById('inspect-fppg').textContent = `${fppg} FPPG`;
      document.getElementById('inspect-college').textContent = p.college || 'Unknown';
      document.getElementById('inspect-draft').textContent = p.draft_year ? `${p.draft_year} Round ${p.draft_round || 1}, Pick ${p.draft_pick || 1}` : 'Undrafted Free Agent';

      const photoEl = document.getElementById('inspect-photo');
      if (photoEl) {
        if (photoUrl) {
          photoEl.src = photoUrl;
          photoEl.style.display = 'block';
        } else {
          photoEl.style.display = 'none';
        }
      }

      modal.style.display = 'flex';
      window.soundEngine.playClick();
    } catch (e) {
      console.error('Error opening inspect modal:', e);
    }
  }
}

window.CardsEngine = CardsEngine;
