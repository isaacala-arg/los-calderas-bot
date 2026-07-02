import { test } from "node:test";
import assert from "node:assert/strict";
import {
  detectarIntent, siguienteVariante, extraerTema,
  sugerirContenido, formatearCancion, BUENOS_DIAS,
} from "./worker.js";

test("detectarIntent clasifica los comandos de Isaac", () => {
  assert.equal(detectarIntent("Buenos días").tipo, "buenos_dias");
  assert.equal(detectarIntent("/bd").tipo, "buenos_dias");
  assert.equal(detectarIntent("canción del día: Nights - Frank Ocean").tipo, "cancion");
  assert.equal(detectarIntent("¿qué subo hoy?").tipo, "que_subo");
  assert.equal(detectarIntent("que subo hoy").tipo, "que_subo");
  assert.equal(detectarIntent("guion sobre el nuevo BYD").tipo, "guion");
  assert.equal(detectarIntent("hazme un guión de los aranceles").tipo, "guion");
  assert.equal(detectarIntent("dame una historia para hoy").tipo, "historia");
  assert.equal(detectarIntent("/start").tipo, "ayuda");
  assert.equal(detectarIntent("oye y si grabo en la noche?").tipo, "chat");
});

test("extraerTema limpia el prefijo del comando", () => {
  assert.equal(extraerTema("guion sobre el nuevo BYD"), "el nuevo BYD");
  assert.equal(extraerTema("hazme un guión de los aranceles a China"), "los aranceles a China");
});

test("siguienteVariante nunca repite y respeta rango", () => {
  for (let i = 0; i < 50; i++) {
    const v = siguienteVariante(2, 4);
    assert.notEqual(v, 2);
    assert.ok(v >= 0 && v < 4);
  }
});

test("BUENOS_DIAS trae las 4 variantes de la spec", () => {
  assert.equal(BUENOS_DIAS.length, 4);
  assert.ok(BUENOS_DIAS.some((v) => v.includes("qué tal amanecieron")));
});

test("sugerirContenido: 2+ reels esta semana -> carrusel", () => {
  const s = sugerirContenido({ trend: 1, howto: 1, carrusel: 0 }, 3);
  assert.ok(s.toLowerCase().includes("carrusel"));
});

test("sugerirContenido: pocos reels -> sugiere reel del pilar menos usado", () => {
  const s = sugerirContenido({ trend: 1 }, 3);
  assert.ok(s.toLowerCase().includes("reel"));
});

test("formatearCancion con y sin canción", () => {
  assert.equal(
    formatearCancion("Nights - Frank Ocean"),
    "🎵 Canción del día: Nights — Frank Ocean"
  );
  assert.ok(formatearCancion("").includes("¿cuál canción?"));
});

test("detectarIntent: mencionar 'guion de' conversacional NO dispara guion", () => {
  assert.equal(detectarIntent("el guion de ayer me quedó bien").tipo, "chat");
  assert.equal(detectarIntent("necesito feedback del guion de la semana pasada").tipo, "chat");
});

test("detectarIntent: formas explícitas SÍ disparan guion con tema", () => {
  assert.deepEqual(detectarIntent("guion sobre el nuevo BYD"), { tipo: "guion", arg: "el nuevo BYD" });
  assert.equal(detectarIntent("hazme un guión de los aranceles").tipo, "guion");
  assert.equal(detectarIntent("quiero un guion sobre el FSD en CDMX").tipo, "guion");
  assert.equal(detectarIntent("hazme un guion").arg, "");
});
