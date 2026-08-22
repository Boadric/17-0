/**
 * 17-0 Stadium Canvas Engine
 * 60 FPS Ambient Stadium Lighting, Volumetric Floodlights & Fog Particles
 */

class StadiumCanvasEngine {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.particles = [];
    this.spotlights = [];
    this.width = window.innerWidth;
    this.height = window.innerHeight;
    this.time = 0;
    this.running = false;

    this.init();
  }

  init() {
    this.resize();
    window.addEventListener('resize', () => this.resize());

    // Initialize ambient dust / turf fog particles
    const particleCount = Math.min(45, Math.floor((this.width * this.height) / 25000));
    for (let i = 0; i < particleCount; i++) {
      this.particles.push({
        x: Math.random() * this.width,
        y: Math.random() * this.height,
        radius: 1 + Math.random() * 2.5,
        vx: (Math.random() - 0.5) * 0.3,
        vy: -0.1 - Math.random() * 0.3,
        alpha: 0.1 + Math.random() * 0.25,
        pulseSpeed: 0.02 + Math.random() * 0.02,
        pulsePhase: Math.random() * Math.PI * 2,
      });
    }

    // Initialize 4 sweeping stadium floodlights
    this.spotlights = [
      { originX: 0.15, speed: 0.0008, width: 0.25, color: 'rgba(14, 165, 233, 0.08)' },
      { originX: 0.85, speed: -0.0009, width: 0.25, color: 'rgba(56, 189, 248, 0.07)' },
      { originX: 0.35, speed: 0.0011, width: 0.3, color: 'rgba(245, 158, 11, 0.06)' },
      { originX: 0.65, speed: -0.0007, width: 0.3, color: 'rgba(147, 51, 234, 0.06)' },
    ];

    this.start();
  }

  resize() {
    if (!this.canvas) return;
    this.width = window.innerWidth;
    this.height = window.innerHeight;
    this.canvas.width = this.width;
    this.canvas.height = this.height;
  }

  start() {
    this.running = true;
    const loop = () => {
      if (!this.running) return;
      this.render();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  stop() {
    this.running = false;
  }

  render() {
    this.time += 1;
    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    ctx.clearRect(0, 0, w, h);

    // 1. Deep Stadium Night Sky Gradient
    const bgGrad = ctx.createRadialGradient(w / 2, h * 0.2, 50, w / 2, h / 2, Math.max(w, h));
    bgGrad.addColorStop(0, '#0f172a');
    bgGrad.addColorStop(0.5, '#090d16');
    bgGrad.addColorStop(1, '#04060a');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, w, h);

    // 2. Draw Sweeping Volumetric Stadium Spotlights
    this.spotlights.forEach((spot, idx) => {
      const angle = Math.sin(this.time * spot.speed + idx) * 0.45;
      const startX = w * spot.originX;
      const startY = 0;
      const targetX = w * 0.5 + Math.tan(angle) * h;
      const targetY = h * 1.1;
      const beamSpread = w * spot.width;

      const beamGrad = ctx.createLinearGradient(startX, startY, targetX, targetY);
      beamGrad.addColorStop(0, spot.color.replace('0.08', '0.2').replace('0.07', '0.18').replace('0.06', '0.15'));
      beamGrad.addColorStop(0.6, spot.color);
      beamGrad.addColorStop(1, 'rgba(0,0,0,0)');

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(startX - 20, startY);
      ctx.lineTo(startX + 20, startY);
      ctx.lineTo(targetX + beamSpread, targetY);
      ctx.lineTo(targetX - beamSpread, targetY);
      ctx.closePath();
      ctx.fillStyle = beamGrad;
      ctx.fill();
      ctx.restore();
    });

    // 3. Subtle Crowd Flash Simulation
    if (Math.random() < 0.03) {
      const flashX = Math.random() * w;
      const flashY = Math.random() * (h * 0.35);
      const flashGrad = ctx.createRadialGradient(flashX, flashY, 1, flashX, flashY, 40);
      flashGrad.addColorStop(0, 'rgba(255, 255, 255, 0.4)');
      flashGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = flashGrad;
      ctx.beginPath();
      ctx.arc(flashX, flashY, 40, 0, Math.PI * 2);
      ctx.fill();
    }

    // 4. Draw Floating Ambient Stadium Dust & Turf Fog Particles
    ctx.save();
    this.particles.forEach((p) => {
      p.x += p.vx;
      p.y += p.vy;
      p.pulsePhase += p.pulseSpeed;

      // Wrap edges
      if (p.x < 0) p.x = w;
      if (p.x > w) p.x = 0;
      if (p.y < 0) p.y = h;
      if (p.y > h) p.y = 0;

      const alpha = p.alpha + Math.sin(p.pulsePhase) * 0.08;
      ctx.fillStyle = `rgba(226, 232, 240, ${Math.max(0, Math.min(1, alpha))})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.restore();

    // 5. Tactile Stadium Table Glow / Spotlight Beam on Center Desk
    const tableLight = ctx.createRadialGradient(w / 2, h * 0.65, 80, w / 2, h * 0.65, w * 0.65);
    tableLight.addColorStop(0, 'rgba(14, 165, 233, 0.12)');
    tableLight.addColorStop(0.5, 'rgba(245, 158, 11, 0.05)');
    tableLight.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = tableLight;
    ctx.fillRect(0, 0, w, h);
  }
}

window.StadiumCanvasEngine = StadiumCanvasEngine;
