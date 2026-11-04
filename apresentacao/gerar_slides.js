const pptxgen = require("pptxgenjs");
const path = require("path");

const FIG = "C:/Users/alexa/Desktop/Faculdade/8° periodo/TCC/Agro Visible/reports/figures/";
const OUT = "C:/Users/alexa/Desktop/Faculdade/8° periodo/TCC/Agro Visible/apresentacao/AgroVisible_apresentacao_parcial.pptx";

const C = {
  dark: "3B2416",   // café torrado
  brown: "6B4226",
  green: "3F6B3A",  // folha
  amber: "C98A2B",
  red: "A8402E",
  tint: "F1ECE7",
  tintG: "E8EFE6",
  text: "2A2420",
  muted: "6E645D",
  white: "FFFFFF",
};
const H = "Cambria", B = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625
pres.author = "Alexandre Marques Spinola Cardoso";
pres.title = "AgroVisible: apresentação parcial do TCC";

function header(slide, step, title, sub) {
  slide.background = { color: C.white };
  slide.addShape(pres.shapes.OVAL, { x: 0.5, y: 0.38, w: 0.56, h: 0.56, fill: { color: C.dark } });
  slide.addText(String(step), { x: 0.5, y: 0.38, w: 0.56, h: 0.56, align: "center", valign: "middle", fontFace: H, fontSize: 18, bold: true, color: C.white, margin: 0, isTextBox: true });
  slide.addText(title, { x: 1.2, y: 0.3, w: 8.3, h: 0.5, fontFace: H, fontSize: 26, bold: true, color: C.dark, margin: 0, valign: "middle", isTextBox: true });
  if (sub) slide.addText(sub, { x: 1.2, y: 0.8, w: 8.3, h: 0.3, fontFace: B, fontSize: 13, color: C.muted, margin: 0, valign: "middle", isTextBox: true });
}
function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill || C.tint }, line: { color: fill || C.tint, width: 0 } });
}
function stat(slide, x, y, w, big, label, color) {
  slide.addText(big, { x, y, w, h: 0.62, fontFace: H, fontSize: 32, bold: true, color: color || C.green, margin: 0, isTextBox: true });
  slide.addText(label, { x, y: y + 0.62, w, h: 0.4, fontFace: B, fontSize: 12, color: C.muted, margin: 0, valign: "top", isTextBox: true });
}

// ---------------------------------------------------------------- 1. Título
{
  const s = pres.addSlide();
  s.background = { color: C.dark };
  s.addText("AgroVisible", { x: 0.6, y: 1.0, w: 8.8, h: 1.0, fontFace: H, fontSize: 54, bold: true, color: C.white, margin: 0, isTextBox: true });
  s.addText("Ferramenta de apoio prescritivo à decisão baseada em aprendizado profundo e programação dinâmica para maximização do lucro do cafeicultor", { x: 0.6, y: 2.05, w: 7.6, h: 1.0, fontFace: B, fontSize: 18, color: "E9DCCB", margin: 0, valign: "top", isTextBox: true });
  s.addText("Apresentação parcial do TCC  ·  Sistemas de Informação  ·  UFLA", { x: 0.6, y: 3.45, w: 8.8, h: 0.35, fontFace: B, fontSize: 14, bold: true, color: C.amber, margin: 0, isTextBox: true });
  s.addText([
    { text: "Alexandre Marques Spinola Cardoso", options: { breakLine: true } },
    { text: "Orientador: Prof. Gustavo Andrade do Vale  ·  Coorientador: Prof. Paulo Henrique Sales" },
  ], { x: 0.6, y: 4.2, w: 8.8, h: 0.7, fontFace: B, fontSize: 13, color: "D9CBB9", margin: 0, valign: "top", isTextBox: true });
  s.addNotes("Olá. Eu sou o Alexandre e vou apresentar o andamento do meu TCC, o AgroVisible. A ideia é mostrar o pipeline completo que já está funcionando: de onde vêm os dados, como construímos as variáveis, como treinamos a rede de previsão, contra quais baselines comparamos e como o grafo de decisão transforma a previsão em uma recomendação de venda.");
}

// ---------------------------------------------------------------- 2. Problema e pipeline
{
  const s = pres.addSlide();
  header(s, 1, "O problema: vender agora ou armazenar?", "O cafeicultor é tomador de preço e decide sob incerteza, com custo para esperar");
  s.addText([
    { text: "Depois da colheita, o produtor precisa decidir quando vender.", options: { breakLine: true } },
    { text: "Esperar pode render mais, mas custa armazenagem, quebra de peso e juros que deixam de ser ganhos.", options: { breakLine: true } },
    { text: "A literatura de IA para café para na previsão de preço. Não diz o que fazer com ela." },
  ], { x: 0.5, y: 1.45, w: 4.1, h: 2.5, fontFace: B, fontSize: 15, color: C.text, margin: 0, valign: "top", paraSpaceAfter: 10, isTextBox: true });
  card(s, 0.5, 4.1, 4.1, 0.95, C.tintG);
  s.addText("Objetivo: prescrever quando vender, armazenar ou travar o preço, maximizando a receita líquida.", { x: 0.7, y: 4.1, w: 3.7, h: 0.95, fontFace: B, fontSize: 13.5, bold: true, color: C.green, margin: 0, valign: "middle", isTextBox: true });

  const steps = [
    ["Coleta", "7 fontes públicas, série diária desde 2005"],
    ["Engenharia de features", "26 variáveis estacionárias, sem vazamento temporal"],
    ["Previsão (LSTM)", "Retorno do preço em 21, 63 e 126 dias úteis"],
    ["Decisão (grafo)", "Programação dinâmica: vender, armazenar ou hedge"],
  ];
  steps.forEach((st, i) => {
    const y = 1.45 + i * 0.93;
    card(s, 5.1, y, 4.4, 0.75);
    s.addShape(pres.shapes.OVAL, { x: 5.25, y: y + 0.15, w: 0.45, h: 0.45, fill: { color: i === 3 ? C.green : C.brown } });
    s.addText(String(i + 1), { x: 5.25, y: y + 0.15, w: 0.45, h: 0.45, align: "center", valign: "middle", fontFace: H, fontSize: 14, bold: true, color: C.white, margin: 0, isTextBox: true });
    s.addText(st[0], { x: 5.85, y: y + 0.07, w: 3.5, h: 0.3, fontFace: B, fontSize: 14, bold: true, color: C.dark, margin: 0, isTextBox: true });
    s.addText(st[1], { x: 5.85, y: y + 0.37, w: 3.5, h: 0.3, fontFace: B, fontSize: 11.5, color: C.muted, margin: 0, isTextBox: true });
  });
  s.addNotes("O problema é o dilema pós-colheita. O produtor colheu o café e precisa decidir se vende agora ou se armazena esperando um preço melhor. Esperar tem custo: armazenagem, perda de peso do grão e o dinheiro que ele deixa de aplicar. Os trabalhos que encontramos no mapeamento sistemático param na previsão do preço e medem só o erro estatístico. O nosso objetivo é ir além: entregar uma prescrição. O pipeline tem quatro etapas, que são os próximos slides: coleta, engenharia de features, previsão com LSTM e o motor de decisão em grafo.");
}

// ---------------------------------------------------------------- 3. Coleta
{
  const s = pres.addSlide();
  header(s, 2, "Coleta de dados", "Todas as fontes são públicas; a coleta é automatizada em Python, exceto o CEPEA");
  stat(s, 0.5, 1.3, 2.8, "5.169", "dias úteis na base final, sem valores faltantes");
  stat(s, 3.6, 1.3, 2.8, "2005–2026", "de 07/12/2005 a 31/08/2026, frequência diária");
  stat(s, 6.7, 1.3, 2.8, "7 fontes", "alinhadas no calendário do indicador CEPEA");

  const src = [
    ["CEPEA/ESALQ", "Preço físico do arábica (alvo) e do robusta, R$/saca"],
    ["ICE Nova York", "Futuro Coffee C, via Yahoo Finance"],
    ["Banco Central", "Câmbio PTAX e meta Selic, via python-bcb"],
    ["Open-Meteo (ERA5)", "Chuva e temperatura mínima em 4 regiões produtoras"],
    ["CFTC", "Posição dos fundos especulativos (relatório COT)"],
    ["Banco Mundial", "Ureia e petróleo, relatório mensal Pink Sheet"],
  ];
  src.forEach((it, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 0.5 + col * 3.07, y = 2.6 + row * 1.12;
    card(s, x, y, 2.86, 0.95);
    s.addText(it[0], { x: x + 0.15, y: y + 0.1, w: 2.56, h: 0.3, fontFace: B, fontSize: 13.5, bold: true, color: C.dark, margin: 0, isTextBox: true });
    s.addText(it[1], { x: x + 0.15, y: y + 0.4, w: 2.56, h: 0.5, fontFace: B, fontSize: 11, color: C.muted, margin: 0, valign: "top", isTextBox: true });
  });
  s.addText("Sétima fonte: CONAB, custo de produção (COE e COT) por safra em Guaxupé, usado pelo motor de decisão.", { x: 0.5, y: 4.9, w: 9.0, h: 0.3, fontFace: B, fontSize: 11.5, italic: true, color: C.muted, margin: 0, isTextBox: true });
  s.addNotes("Na coleta usamos sete fontes públicas. O alvo é o indicador CEPEA/ESALQ do café arábica, que é o preço físico de referência do produtor em Minas e São Paulo. Dele também vem o preço do robusta. Da bolsa de Nova York vem o contrato futuro Coffee C. Do Banco Central, o câmbio PTAX e a Selic. O clima vem da reanálise ERA5, pela API Open-Meteo, em Varginha, Patrocínio, Franca e Colatina. Da CFTC vem a posição dos fundos especulativos, e do Banco Mundial o preço da ureia e do petróleo. Por fim, a CONAB fornece o custo de produção. A base final tem 5.169 dias úteis, de dezembro de 2005 a agosto de 2026, sem valores faltantes. Um detalhe: o site do CEPEA bloqueia acesso automatizado, então essas planilhas são baixadas manualmente.");
}

// ---------------------------------------------------------------- 4. Série e partição
{
  const s = pres.addSlide();
  header(s, 2, "A série temporal e a partição", "Corte estritamente cronológico por ano-safra; o teste nunca é visto no treino");
  s.addImage({ path: FIG + "01_serie_cepea_particao.png", x: 0.5, y: 1.25, w: 9.0, h: 3.11 });
  const parts = [
    ["Treino", "2005 a jun/2022", "3.940 amostras", C.green],
    ["Validação", "jul/2022 a jun/2024", "372 amostras", C.amber],
    ["Teste cego", "jul/2024 a ago/2026", "417 amostras", C.red],
  ];
  parts.forEach((p, i) => {
    const x = 0.5 + i * 3.07;
    s.addShape(pres.shapes.OVAL, { x, y: 4.62, w: 0.22, h: 0.22, fill: { color: p[3] } });
    s.addText([{ text: p[0] + "  ", options: { bold: true, color: C.dark } }, { text: p[1] + "  ·  " + p[2], options: { color: C.muted } }], { x: x + 0.32, y: 4.52, w: 2.75, h: 0.42, fontFace: B, fontSize: 10, margin: 0, valign: "middle", isTextBox: true });
  });
  s.addNotes("Aqui está a série do preço do arábica em reais por saca, com a partição. O treino vai de 2005 até junho de 2022, com 3.940 amostras, e inclui a geada de 2021. A validação cobre as safras 2022/23 e 2023/24, e é usada para a parada antecipada do treino e para medir a incerteza da previsão. O teste cego cobre as safras 2024/25 e 2025/26, que foi um período de preço recorde, chegando a mais de 2.700 reais. A partição é por ano-safra porque o café tem bienalidade, então usamos sempre pares de safras.");
}

// ---------------------------------------------------------------- 5. Features
{
  const s = pres.addSlide();
  header(s, 3, "Engenharia de features", "26 variáveis em 6 grupos, todas estacionárias; janela de entrada de 63 dias úteis");
  const g = [
    ["Retornos e médias móveis", "9", "Retorno do arábica, robusta, ICE e PTAX; preço contra médias de 1 mês a 2 anos"],
    ["Mercado", "3", "Volatilidade de 21 dias, razão arábica/robusta, base físico contra futuro"],
    ["Calendário e macro", "4", "Mês em seno e cosseno, bienalidade, meta Selic"],
    ["Clima", "5", "Chuva de 30 e 90 dias, mínima de 7 dias, indicador de geada, chuva no ES"],
    ["Fundos", "2", "Posição líquida dos especuladores e sua variação em 4 semanas"],
    ["Insumos", "3", "Relação de troca café por ureia, retorno anual da ureia e do petróleo"],
  ];
  g.forEach((it, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 0.5 + col * 3.07, y = 1.3 + row * 1.42;
    card(s, x, y, 2.86, 1.25);
    s.addText(it[1], { x: x + 0.15, y: y + 0.12, w: 0.6, h: 0.5, fontFace: H, fontSize: 26, bold: true, color: C.green, margin: 0, valign: "middle", isTextBox: true });
    s.addText(it[0], { x: x + 0.75, y: y + 0.12, w: 2.0, h: 0.5, fontFace: B, fontSize: 13, bold: true, color: C.dark, margin: 0, valign: "middle", isTextBox: true });
    s.addText(it[2], { x: x + 0.15, y: y + 0.65, w: 2.56, h: 0.55, fontFace: B, fontSize: 10.5, color: C.muted, margin: 0, valign: "top", isTextBox: true });
  });
  card(s, 0.5, 4.2, 9.0, 0.95, C.tintG);
  s.addText([
    { text: "Cuidados contra vazamento de dados: ", options: { bold: true, color: C.green } },
    { text: "cada série entra na data em que foi divulgada, não na data a que se refere; lacunas são preenchidas só com o último valor conhecido; a normalização é ajustada apenas no treino.", options: { color: C.text } },
  ], { x: 0.7, y: 4.2, w: 8.6, h: 0.95, fontFace: B, fontSize: 12.5, margin: 0, valign: "middle", isTextBox: true });
  s.addNotes("Na engenharia de features, transformamos as séries brutas em 26 variáveis, em seis grupos. O primeiro grupo são retornos e a posição do preço em relação a médias móveis. O segundo é de mercado: volatilidade, a razão entre arábica e robusta e a base, que é a diferença entre o preço físico e o futuro. Depois calendário e macro, com a sazonalidade do mês, a bienalidade e a Selic. O clima tem chuva acumulada, temperatura mínima e um indicador de geada. Fundos é a posição dos especuladores na bolsa. E insumos traz a relação de troca, quantas sacas de café compram uma tonelada de ureia. Todas são estacionárias por construção, e não usamos o preço em nível. O ponto mais importante é o cuidado com vazamento: por exemplo, o relatório dos fundos é de terça mas só sai na sexta, então a variável entra na sexta.");
}

// ---------------------------------------------------------------- 6. Treinamento
{
  const s = pres.addSlide();
  header(s, 4, "Treinamento da LSTM", "Uma rede, três saídas treinadas em conjunto: retorno em 21, 63 e 126 dias úteis");
  const layers = [
    ["Entrada", "63 dias × 26 variáveis", C.brown],
    ["LSTM 64", "dropout 0,2", C.dark],
    ["LSTM 32", "dropout 0,2", C.dark],
    ["Densa 32", "ReLU", C.dark],
    ["Saída", "3 log-retornos", C.green],
  ];
  layers.forEach((l, i) => {
    const y = 1.35 + i * 0.74;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y, w: 2.9, h: 0.56, rectRadius: 0.08, fill: { color: l[2] }, line: { color: l[2], width: 0 } });
    s.addText([{ text: l[0], options: { bold: true, fontSize: 13.5 } }, { text: "   " + l[1], options: { fontSize: 11 } }], { x: 0.5, y, w: 2.9, h: 0.56, align: "center", valign: "middle", fontFace: B, color: C.white, margin: 0, isTextBox: true });
    if (i < layers.length - 1) s.addText("▼", { x: 0.5, y: y + 0.55, w: 2.9, h: 0.2, align: "center", valign: "middle", fontSize: 9, color: C.muted, margin: 0, isTextBox: true });
  });
  s.addImage({ path: FIG + "02_curva_perda.png", x: 3.9, y: 1.3, w: 5.6, h: 2.45 });
  s.addText([
    { text: "Alvo: log-retorno futuro, não o preço em nível", options: { bullet: true, breakLine: true } },
    { text: "Perda MSE, otimizador Adam, parada antecipada na validação", options: { bullet: true, breakLine: true } },
    { text: "Parou na época 55; treino de 2 minutos em CPU", options: { bullet: true, breakLine: true } },
    { text: "Hiperparâmetros fixados antes, sem busca na validação", options: { bullet: true } },
  ], { x: 3.9, y: 3.85, w: 5.6, h: 1.3, fontFace: B, fontSize: 12.5, color: C.text, margin: 0, valign: "top", paraSpaceAfter: 3, isTextBox: true });
  s.addNotes("A rede é uma LSTM empilhada. Ela recebe uma janela de 63 dias úteis com as 26 variáveis, passa por duas camadas LSTM com dropout, uma camada densa e produz três saídas ao mesmo tempo: o retorno do preço em 21, 63 e 126 dias úteis, ou seja, um, três e seis meses. Uma decisão importante foi prever o log-retorno e não o preço em nível, porque o preço tem tendência e a rede aprenderia só a repetir o último valor. O treino usa erro quadrático, Adam e parada antecipada. Ele parou na época 55 e leva cerca de dois minutos em CPU. O gráfico mostra a curva de perda, e dá para ver a distância entre treino e validação, que é um sinal de sobreajuste que tratamos como limitação.");
}

// ---------------------------------------------------------------- 7. Previsão
{
  const s = pres.addSlide();
  header(s, 4, "Previsão no teste cego", "Previsto contra realizado por horizonte, safras 2024/25 e 2025/26");
  s.addImage({ path: FIG + "03_previsto_realizado_teste.png", x: 0.5, y: 1.25, w: 4.36, h: 4.0 });
  stat(s, 5.3, 1.3, 4.2, "79 %", "de acerto de direção no horizonte de 126 dias");
  stat(s, 5.3, 2.5, 4.2, "58 %", "de acerto de direção em 21 dias: o curto prazo é quase ruído", C.amber);
  card(s, 5.3, 3.75, 4.2, 1.4);
  s.addText([
    { text: "Como a incerteza chega à decisão", options: { bold: true, color: C.dark, breakLine: true } },
    { text: "O desvio-padrão dos erros na validação, por horizonte, define a largura do cone de preços que o motor de decisão enxerga.", options: { color: C.text } },
  ], { x: 5.5, y: 3.75, w: 3.8, h: 1.4, fontFace: B, fontSize: 12.5, margin: 0, valign: "middle", paraSpaceAfter: 4, isTextBox: true });
  s.addNotes("Este é o resultado da previsão no teste cego, nos três horizontes. O ponto principal é que a rede acerta a direção do movimento em 79 por cento dos casos no horizonte de seis meses. No horizonte de um mês o acerto é de 58 por cento, bem mais perto do acaso, o que é esperado: no curto prazo o preço é quase um passeio aleatório. A principal fraqueza é que a rede comprime as previsões para perto de zero, então ela acerta a direção mas subestima a magnitude dos grandes movimentos. Além do valor previsto, guardamos o desvio-padrão dos erros em cada horizonte, e é esse número que vira a incerteza no motor de decisão.");
}

// ---------------------------------------------------------------- 8. Baselines
{
  const s = pres.addSlide();
  header(s, 5, "Baselines: a rede supera o quê?", "RMSE do log-retorno no teste cego; quanto menor, melhor");
  s.addChart(pres.charts.BAR, [
    { name: "LSTM", labels: ["21 dias", "63 dias", "126 dias"], values: [0.147, 0.213, 0.267] },
    { name: "Passeio aleatório", labels: ["21 dias", "63 dias", "126 dias"], values: [0.120, 0.233, 0.321] },
    { name: "ARIMA(1,1,2)", labels: ["21 dias", "63 dias", "126 dias"], values: [0.119, 0.233, 0.321] },
    { name: "Curva de futuros", labels: ["21 dias", "63 dias", "126 dias"], values: [0.130, 0.227, 0.309] },
  ], {
    x: 0.4, y: 1.25, w: 5.5, h: 3.95, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
    chartColors: [C.green, "B9AFA6", "8A7F77", C.amber],
    showLegend: true, legendPos: "b", legendFontSize: 11, legendFontFace: B, legendColor: C.text,
    showValue: true, dataLabelFormatCode: "0.00", dataLabelFontSize: 9, dataLabelColor: C.text, dataLabelPosition: "outEnd",
    catAxisLabelColor: C.text, catAxisLabelFontSize: 12, catAxisLabelFontFace: B,
    valAxisLabelColor: C.muted, valAxisLabelFontSize: 10, valAxisMaxVal: 0.36, valAxisMinVal: 0, valAxisHidden: true,
    valGridLine: { color: "E6E0DA", size: 0.5 }, catGridLine: { style: "none" },
  });
  const bl = [
    ["Passeio aleatório", "Retorno previsto igual a zero: o preço de amanhã é o de hoje."],
    ["ARIMA", "Modelo estatístico clássico. Ficou igual ao passeio aleatório."],
    ["Curva de futuros", "Preço futuro da bolsa ajustado pela base sazonal. É a expectativa que o produtor já tem de graça."],
  ];
  bl.forEach((b, i) => {
    const y = 1.3 + i * 0.95;
    card(s, 6.2, y, 3.3, 0.82);
    s.addText(b[0], { x: 6.35, y: y + 0.06, w: 3.0, h: 0.26, fontFace: B, fontSize: 12.5, bold: true, color: C.dark, margin: 0, isTextBox: true });
    s.addText(b[1], { x: 6.35, y: y + 0.32, w: 3.0, h: 0.48, fontFace: B, fontSize: 10.5, color: C.muted, margin: 0, valign: "top", isTextBox: true });
  });
  card(s, 6.2, 4.2, 3.3, 0.95, C.tintG);
  s.addText("A LSTM perde em 21 dias e vence todos os baselines em 63 e 126 dias.", { x: 6.35, y: 4.2, w: 3.0, h: 0.95, fontFace: B, fontSize: 12.5, bold: true, color: C.green, margin: 0, valign: "middle", isTextBox: true });
  s.addNotes("Para saber se a rede agrega alguma coisa, comparamos com três baselines. O passeio aleatório diz que o retorno previsto é zero. O ARIMA é o modelo estatístico clássico, e ele ficou praticamente igual ao passeio aleatório. O terceiro é o mais exigente: a curva de futuros da bolsa ajustada pela base sazonal, que é a expectativa de preço que o produtor já tem sem modelo nenhum. No gráfico, quanto menor a barra, melhor. Em 21 dias a LSTM perde para todos. Em 63 e 126 dias ela vence todos no teste. Vale registrar que na validação a curva de futuros ganhou da rede em 63 dias, então o resultado depende do regime de mercado. Também fizemos um estudo de ablação, que mostrou que os grupos de mercado e calendário são os que carregam o sinal de longo prazo.");
}

// ---------------------------------------------------------------- 9. Grafo
{
  const s = pres.addSlide();
  header(s, 6, "O grafo de decisão", "Processo de decisão de Markov resolvido por indução retroativa (equação de Bellman)");
  s.addImage({ path: FIG + "05_arvore_decisoes.png", x: 4.3, y: 1.25, w: 5.2, h: 2.6 });
  s.addText("Árvore reduzida para visualização. O motor real resolve 7 meses × 121 níveis de preço.", { x: 4.3, y: 3.87, w: 5.2, h: 0.3, fontFace: B, fontSize: 10.5, italic: true, color: C.muted, margin: 0, isTextBox: true });
  const items = [
    ["Nós", "Preço possível em cada mês, de hoje até 6 meses"],
    ["Arestas", "Probabilidade de transição, vinda da previsão e do erro da LSTM"],
    ["Ações", "Vender, armazenar ou armazenar com hedge em futuros"],
    ["Custos", "Armazenagem, quebra de peso e custo de oportunidade (Selic)"],
  ];
  items.forEach((it, i) => {
    const y = 1.3 + i * 0.68;
    s.addShape(pres.shapes.OVAL, { x: 0.5, y: y + 0.05, w: 0.4, h: 0.4, fill: { color: i === 2 ? C.green : C.brown } });
    s.addText(it[0], { x: 1.05, y, w: 3.0, h: 0.25, fontFace: B, fontSize: 13, bold: true, color: C.dark, margin: 0, isTextBox: true });
    s.addText(it[1], { x: 1.05, y: y + 0.25, w: 3.0, h: 0.38, fontFace: B, fontSize: 10.5, color: C.muted, margin: 0, valign: "top", isTextBox: true });
  });
  card(s, 0.5, 4.3, 9.0, 0.85);
  s.addText([
    { text: "Valor de cada nó", options: { bold: true, color: C.dark } },
    { text: "  =  o maior entre  ", options: { color: C.muted } },
    { text: "vender agora", options: { bold: true, color: C.red } },
    { text: " ,  ", options: { color: C.muted } },
    { text: "armazenar e seguir", options: { bold: true, color: C.green } },
    { text: "  (valor esperado do mês seguinte, descontado, menos custos)  e  ", options: { color: C.muted } },
    { text: "hedge", options: { bold: true, color: C.brown } },
  ], { x: 0.7, y: 4.3, w: 8.6, h: 0.85, fontFace: B, fontSize: 12.5, margin: 0, valign: "middle", isTextBox: true });
  s.addNotes("Esta é a parte prescritiva. Modelamos a venda como um processo de decisão de Markov. O grafo tem camadas, uma por mês, de hoje até seis meses. Cada nó é um preço possível naquele mês. As arestas ligam um mês ao seguinte, com probabilidades que vêm da previsão da LSTM e do erro histórico dela. Em cada nó o produtor tem três ações: vender, armazenar, ou armazenar travando o preço no mercado futuro. Resolvemos de trás para frente, com a equação de Bellman: no último mês só resta vender, e em cada mês anterior o valor do nó é o maior entre vender agora e o valor esperado de continuar, já descontando armazenagem, quebra e a Selic. A figura é uma árvore reduzida só para visualizar. Verde é armazenar e vermelho é vender. Neste exemplo, de agosto de 2026, a recomendação é armazenar por dois meses e vender a partir do terceiro. O motor real usa 121 níveis de preço por mês e resolve em 2 milissegundos.");
}

// ---------------------------------------------------------------- 10. Resultados
{
  const s = pres.addSlide();
  header(s, 7, "Resultado do backtest", "Receita líquida média por saca em 38 decisões mensais, 4 safras (2022/23 a 2025/26)");
  s.addChart(pres.charts.BAR, [
    { name: "R$/saca", labels: ["Hedge 6 meses", "Venda parcelada", "Média móvel", "Venda imediata", "Meta sobre COE", "AgroVisible", "Oráculo"], values: [1459, 1512, 1527, 1562, 1573, 1596, 1755] },
  ], {
    x: 0.4, y: 1.25, w: 5.7, h: 3.95, barDir: "bar", barGapWidthPct: 45,
    chartColors: ["B9AFA6", "B9AFA6", "B9AFA6", "8A7F77", "B9AFA6", C.green, "D9C7A6"],
    showLegend: false, showValue: true, dataLabelFormatCode: "0", dataLabelFontSize: 11, dataLabelColor: C.text, dataLabelPosition: "outEnd",
    catAxisLabelColor: C.text, catAxisLabelFontSize: 11.5, catAxisLabelFontFace: B,
    valAxisHidden: true, valAxisMinVal: 1200, valAxisMaxVal: 1850,
    valGridLine: { style: "none" }, catGridLine: { style: "none" },
  });
  stat(s, 6.5, 1.3, 3.0, "+2,7 %", "sobre a venda imediata, já descontados os custos");
  stat(s, 6.5, 2.45, 3.0, "92 %", "da receita do oráculo, que conhece o futuro");
  card(s, 6.5, 3.65, 3.0, 1.5);
  s.addText([
    { text: "Leitura honesta", options: { bold: true, color: C.dark, breakLine: true } },
    { text: "Ganho significativo contra a venda parcelada (p = 0,018) e marginal contra a imediata (p = 0,066). Na alta de 2024/25 a parcelada foi melhor.", options: { color: C.text } },
  ], { x: 6.65, y: 3.65, w: 2.7, h: 1.5, fontFace: B, fontSize: 11.5, margin: 0, valign: "middle", paraSpaceAfter: 4, isTextBox: true });
  s.addNotes("Para medir se a prescrição vale dinheiro, fizemos um backtest. Em cada mês simulamos um produtor com uma saca, rodamos o motor só com a informação disponível naquela data e executamos a política contra os preços que de fato aconteceram. São 38 decisões em quatro safras. O AgroVisible obteve em média 1.596 reais por saca, contra 1.562 da venda imediata, um ganho de 2,7 por cento já descontados os custos, e capturou 92 por cento do que um oráculo com conhecimento perfeito conseguiria. Ele foi a única estratégia que ficou acima da venda imediata no consolidado. Mas é preciso ser honesto: a diferença é estatisticamente significativa contra a venda parcelada, e apenas marginal contra a venda imediata. E na safra 2024/25, de alta histórica, a venda parcelada foi melhor. A análise de sensibilidade mostrou que a política quase não muda com a Selic, a armazenagem ou a base; só muda com a aversão a risco do produtor.");
}

// ---------------------------------------------------------------- 11. Fechamento
{
  const s = pres.addSlide();
  s.background = { color: C.dark };
  s.addText("Onde estamos e próximos passos", { x: 0.6, y: 0.45, w: 8.8, h: 0.6, fontFace: H, fontSize: 28, bold: true, color: C.white, margin: 0, isTextBox: true });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.35, w: 4.2, h: 3.1, rectRadius: 0.08, fill: { color: "4E3323" }, line: { color: "4E3323", width: 0 } });
  s.addText("Concluído", { x: 0.85, y: 1.5, w: 3.7, h: 0.35, fontFace: B, fontSize: 15, bold: true, color: C.amber, margin: 0, isTextBox: true });
  s.addText([
    { text: "Pipeline completo, da coleta à recomendação", options: { bullet: true, breakLine: true } },
    { text: "LSTM avaliada contra 3 baselines e com ablação", options: { bullet: true, breakLine: true } },
    { text: "Backtest em 4 safras e análise de sensibilidade", options: { bullet: true, breakLine: true } },
    { text: "Texto: 6 dos 8 capítulos escritos", options: { bullet: true } },
  ], { x: 0.85, y: 1.95, w: 3.7, h: 2.3, fontFace: B, fontSize: 13.5, color: "F0E6DA", margin: 0, valign: "top", paraSpaceAfter: 8, isTextBox: true });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.2, y: 1.35, w: 4.2, h: 3.1, rectRadius: 0.08, fill: { color: "4E3323" }, line: { color: "4E3323", width: 0 } });
  s.addText("Próximos passos", { x: 5.45, y: 1.5, w: 3.7, h: 0.35, fontFace: B, fontSize: 15, bold: true, color: C.amber, margin: 0, isTextBox: true });
  s.addText([
    { text: "Introdução, conclusão e revisão final do texto", options: { bullet: true, breakLine: true } },
    { text: "Versão enxuta do modelo para reduzir o sobreajuste", options: { bullet: true, breakLine: true } },
    { text: "Prever o excedente sobre a curva de futuros", options: { bullet: true, breakLine: true } },
    { text: "Entrega do TCC em 10 de novembro", options: { bullet: true } },
  ], { x: 5.45, y: 1.95, w: 3.7, h: 2.3, fontFace: B, fontSize: 13.5, color: "F0E6DA", margin: 0, valign: "top", paraSpaceAfter: 8, isTextBox: true });
  s.addText("Obrigado.", { x: 0.6, y: 4.7, w: 8.8, h: 0.45, fontFace: H, fontSize: 20, bold: true, color: C.white, margin: 0, isTextBox: true });
  s.addNotes("Para fechar: o pipeline está completo e funcionando, da coleta até a recomendação. A rede foi avaliada contra três baselines e com estudo de ablação, o motor foi testado em quatro safras e fizemos a análise de sensibilidade. No texto, seis dos oito capítulos estão escritos. Os próximos passos são escrever a introdução e a conclusão, e, se houver tempo, testar duas melhorias que os resultados sugeriram: uma versão enxuta do modelo, com menos variáveis, e fazer a rede prever só o que a curva de futuros ainda não precifica. A entrega é em 10 de novembro. Obrigado.");
}

pres.writeFile({ fileName: OUT }).then(f => console.log("ok", f));
