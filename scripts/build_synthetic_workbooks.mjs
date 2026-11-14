// B03 values-only source extracts; financial computations are owned by Python.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const qa = path.join(root, 'runtime/b03');
const specs = JSON.parse(await fs.readFile(path.join(qa, 'workbooks.json'), 'utf8'));
const column = n => String.fromCharCode(65+n);
const inspection = [];
for (const spec of specs) {
  const wb = Workbook.create();
  for (const s of spec.sheets) {
    const sheet = wb.worksheets.add(s.name);
    const last = column(s.columns.length-1);
    const end = 5+s.rows.length;
    sheet.showGridLines = false;
    const all = sheet.getRange(`A1:${last}${end}`);
    all.format.font = {name:'Arial', size:11};
    all.format.columnWidth = 21;
    all.format.rowHeight = 26;
    all.format.verticalAlignment = 'center';
    sheet.getRange('A1').values = [[spec.label]];
    sheet.getRange('A1').format.font = {bold:true, color:'#8B2020', size:11};
    sheet.getRange('A2').values = [[s.title]];
    sheet.getRange('A2').format.font = {bold:true, size:14};
    sheet.getRange('A3').values = [[`${spec.borrower} | the Bank | Fictional relationship only`]];
    sheet.getRange('A4').values = [[s.note]];
    sheet.getRange('A4').format.font = {italic:true, size:10, color:'#555555'};
    sheet.getRange(`A5:${last}5`).values = [s.columns];
    sheet.getRange(`A5:${last}5`).format = {
      fill:'#213A54', font:{bold:true, color:'#FFFFFF'}, wrapText:true,
      horizontalAlignment:'center', rowHeight:42,
    };
    const rows = s.rows.map(row => row.map(value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00Z`) : value));
    sheet.getRange(`A6:${last}${end}`).values = rows;
    sheet.getRange(`A6:${last}${end}`).format.wrapText = true;
    for (const [cols, format] of Object.entries(s.formats)) {
      const [a,b] = cols.split(':');
      sheet.getRange(`${a}6:${b}${end}`).setNumberFormat(format);
    }
    rows.forEach((row, ri) => row.forEach((value, ci) => {
      if (value instanceof Date) sheet.getRange(`${column(ci)}${ri+6}`).setNumberFormat('yyyy-mm-dd');
    }));
    for (const [col,width] of Object.entries(s.widths)) sheet.getRange(`${col}1:${col}${end}`).format.columnWidth=width;
    for (let r=6;r<=end;r++) {
      if (r%2===0) sheet.getRange(`A${r}:${last}${r}`).format.fill='#F0F4F8';
      sheet.getRange(`A${r}:${last}${r}`).format.rowHeight=40;
    }
    // Source/assumption descriptions need space; preserve full URLs as text.
    if (s.name==='Sources') sheet.getRange(`A6:${last}${end}`).format.rowHeight=65;
    if (s.name==='Assumptions') sheet.getRange(`A6:${last}${end}`).format.rowHeight=45;
    if (end>20) sheet.freezePanes.freezeRows(5);
  }
  wb.recalculate();
  const prefix = path.basename(spec.file, '.xlsx');
  for (const s of spec.sheets) {
    const last=column(s.columns.length-1);
    const end=5+s.rows.length;
    inspection.push({file:spec.file,sheet:s.name, result:(await wb.inspect({kind:'table', range:`'${s.name}'!A5:${last}${end}`, include:'values,formulas', tableMaxRows:40, tableMaxCols:12, maxChars:6000})).ndjson});
    const blob = await wb.render({sheetName:s.name, range:`A1:${last}${end}`, scale:1.5, format:'png'});
    await fs.writeFile(path.join(qa, `${prefix}-${s.name}.png`),new Uint8Array(await blob.arrayBuffer()));
  }
  const errors=await wb.inspect({kind:'match', searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:30},summary:'B03 final error scan'});
  inspection.push({file:spec.file, errors:errors.ndjson});
  const output=await SpreadsheetFile.exportXlsx(wb);
  const temporary=path.join(qa,`${prefix}.xlsx`);
  await output.save(temporary);
  await fs.rename(temporary,path.join(root,'demo/synthetic',spec.file));
  console.log(`Exported ${spec.file}`);
}
await fs.writeFile(path.join(qa,'workbook-inspection.json'),JSON.stringify(inspection,null,2));
