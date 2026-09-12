// 描画ヘルパー: data-chara 属性の付いた <svg> にキャラを描く
const CAT = (face) => `
<g stroke="#111" stroke-width="8" stroke-linejoin="round" stroke-linecap="round">
  <path d="M60 130 L40 30 L120 90 Z" fill="#fff"/><path d="M340 130 L360 30 L280 90 Z" fill="#fff"/>
  <ellipse cx="200" cy="200" rx="170" ry="140" fill="#fff"/>
  <path d="M60 130 L40 30 L120 90" fill="#f3c9a1"/><path d="M340 130 L360 30 L280 90" fill="#f3c9a1"/>
  <path d="M100 90 Q200 40 300 90 L280 160 Q200 130 120 160 Z" fill="#111" stroke="none"/>
  <path d="M260 250 Q300 240 330 260 L 330 300 Q 290 285 260 300 Z" fill="#e0912e" stroke="none"/>
  ${face}
  <path d="M120 330 Q200 400 280 330 L300 470 Q200 520 100 470 Z" fill="#fff"/>
  <path d="M150 470 L140 560" /><path d="M250 470 L260 560" />
</g>`;
const RABBIT = (face) => `
<g stroke="#111" stroke-width="8" stroke-linejoin="round" stroke-linecap="round">
  <ellipse cx="140" cy="60" rx="38" ry="120" fill="#fff"/><ellipse cx="260" cy="60" rx="38" ry="120" fill="#fff"/>
  <ellipse cx="140" cy="60" rx="16" ry="80" fill="#f7b9c4" stroke="none"/><ellipse cx="260" cy="60" rx="16" ry="80" fill="#f7b9c4" stroke="none"/>
  <ellipse cx="200" cy="220" rx="150" ry="130" fill="#fff"/>
  ${face}
  <path d="M130 340 Q200 400 270 340 L290 480 Q200 530 110 480 Z" fill="#fff"/>
</g>`;
const FACES = {
  normal: `<circle cx="140" cy="200" r="14" fill="#111"/><circle cx="260" cy="200" r="14" fill="#111"/><path d="M180 250 Q200 270 220 250" fill="none"/>`,
  happy: `<path d="M120 200 Q140 180 160 200" fill="none"/><path d="M240 200 Q260 180 280 200" fill="none"/><path d="M160 250 Q200 300 240 250" fill="#fff"/>`,
  shock: `<circle cx="140" cy="200" r="26" fill="#fff"/><circle cx="260" cy="200" r="26" fill="#fff"/><circle cx="140" cy="200" r="6" fill="#111"/><circle cx="260" cy="200" r="6" fill="#111"/><ellipse cx="200" cy="270" rx="26" ry="36" fill="#111"/>`,
  smug: `<path d="M120 190 L160 205" /><path d="M280 190 L240 205" /><path d="M170 255 Q210 285 240 245" fill="none"/>`,
  focus: `<path d="M120 200 L160 200" /><path d="M240 200 L280 200" /><path d="M185 258 L215 258" />`,
  cry: `<path d="M120 190 Q140 215 160 190" fill="none"/><path d="M240 190 Q260 215 280 190" fill="none"/><path d="M170 275 Q200 250 230 275" fill="none"/><path d="M125 215 Q115 250 130 260" fill="#8cf" stroke="#39c" stroke-width="5"/><path d="M275 215 Q285 250 270 260" fill="#8cf" stroke="#39c" stroke-width="5"/>`,
};
for (const el of document.querySelectorAll('svg[data-chara]')) {
  const face = FACES[el.dataset.face || 'normal'];
  el.setAttribute('viewBox', '0 -80 400 660');
  el.innerHTML = el.dataset.chara === 'cat' ? CAT(face) : RABBIT(face);
}
