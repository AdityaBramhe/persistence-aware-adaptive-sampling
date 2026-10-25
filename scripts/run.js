// Run a compiled Arduino Uno hex in the avr8js emulator (the same AVR core Wokwi uses)
// and capture everything the sketch writes to Serial (115200 baud, cycle-accurate).
// usage: node run.js <fw.hex> <out.log> [seconds=61] [adc_volts=0]
const fs = require('fs');
const {
  CPU, avrInstruction, AVRTimer, timer0Config, timer1Config, timer2Config,
  AVRUSART, usart0Config, AVRADC, adcConfig,
} = require('avr8js');

const [hexPath, outPath, secArg, voltArg] = process.argv.slice(2);
const seconds = secArg ? parseFloat(secArg) : 61;
const volts = voltArg ? parseFloat(voltArg) : 0;
const F_CPU = 16e6;

function loadHex(text, target) {
  for (const line of text.split('\n')) {
    if (line[0] !== ':' || line.substr(7, 2) !== '00') continue;
    const bytes = parseInt(line.substr(1, 2), 16);
    const addr = parseInt(line.substr(3, 4), 16);
    for (let i = 0; i < bytes; i++) target[addr + i] = parseInt(line.substr(9 + i * 2, 2), 16);
  }
}

const program = new Uint16Array(0x4000);           // 32 KB flash
loadHex(fs.readFileSync(hexPath, 'utf8'), new Uint8Array(program.buffer));
const cpu = new CPU(program);
new AVRTimer(cpu, timer0Config);
new AVRTimer(cpu, timer1Config);
new AVRTimer(cpu, timer2Config);
const usart = new AVRUSART(cpu, usart0Config, F_CPU);
const adc = new AVRADC(cpu, adcConfig);
for (let i = 0; i < 8; i++) adc.channelValues[i] = volts;   // pots at minimum

const chunks = [];
usart.onByteTransmit = (b) => chunks.push(b);

const limit = Math.floor(seconds * F_CPU);
const t0 = Date.now();
while (cpu.cycles < limit) {
  avrInstruction(cpu);
  cpu.tick();
}
fs.writeFileSync(outPath, Buffer.from(chunks));
console.error(`emulated ${seconds}s in ${((Date.now() - t0) / 1000).toFixed(1)}s wall, ${chunks.length} serial bytes`);
