function firstMatch(source, pattern) {
  const match = pattern.exec(source);
  return match ? match[1].trim() : "";
}

function splitStage15Columns(stageGridMarkup = "") {
  const source = String(stageGridMarkup || "");
  const columnToken = '<div class="stage15-column">';
  const firstColumnOpen = source.indexOf(columnToken);
  if (firstColumnOpen === -1) {
    return {
      firstColumnMarkup: "",
      secondColumnMarkup: ""
    };
  }
  const secondColumnOpen = source.indexOf(columnToken, firstColumnOpen + columnToken.length);
  if (secondColumnOpen === -1) {
    return {
      firstColumnMarkup: "",
      secondColumnMarkup: ""
    };
  }

  const firstColumnSegment = source.slice(firstColumnOpen + columnToken.length, secondColumnOpen).trimEnd();
  const normalizedFirstColumnSegment = firstColumnSegment.endsWith("</div>")
    ? firstColumnSegment.slice(0, -"</div>".length).trimEnd()
    : firstColumnSegment;

  const secondColumnSegment = source.slice(secondColumnOpen + columnToken.length).trim();
  const normalizedSecondColumnSegment = secondColumnSegment.endsWith("</div>")
    ? secondColumnSegment.slice(0, -"</div>".length).trimEnd()
    : secondColumnSegment;

  return {
    firstColumnMarkup: normalizedFirstColumnSegment,
    secondColumnMarkup: normalizedSecondColumnSegment
  };
}

function splitFirstStage15Section(columnMarkup = "") {
  const source = String(columnMarkup || "").trim();
  const sectionToken = '<section class="card">';
  const firstSectionOpen = source.indexOf(sectionToken);
  if (firstSectionOpen === -1) {
    return {
      secondColumnFirstSectionMarkup: "",
      secondColumnRemainingMarkup: ""
    };
  }

  const secondSectionOpen = source.indexOf(sectionToken, firstSectionOpen + sectionToken.length);
  if (secondSectionOpen === -1) {
    return {
      secondColumnFirstSectionMarkup: source,
      secondColumnRemainingMarkup: ""
    };
  }

  return {
    secondColumnFirstSectionMarkup: source.slice(firstSectionOpen, secondSectionOpen).trimEnd(),
    secondColumnRemainingMarkup: source.slice(secondSectionOpen).trim()
  };
}

export function extractStage15ShellDocumentParts(htmlSource = "") {
  const source = String(htmlSource || "");
  const shellMarkup = firstMatch(source, /<body[^>]*>([\s\S]*?)<script type="module">/i);
  const stageGridMarkup = firstMatch(
    shellMarkup,
    /<div class="stage15-grid">([\s\S]*)<\/div>\s*<\/div>\s*<\/main>\s*<\/div>\s*$/i,
  );
  const { firstColumnMarkup, secondColumnMarkup } = splitStage15Columns(stageGridMarkup);
  const { secondColumnFirstSectionMarkup, secondColumnRemainingMarkup } = splitFirstStage15Section(secondColumnMarkup);
  const { secondColumnFirstSectionMarkup: secondColumnSecondSectionMarkup, secondColumnRemainingMarkup: secondColumnTrailingMarkup } =
    splitFirstStage15Section(secondColumnRemainingMarkup);
  return {
    title: firstMatch(source, /<title>([\s\S]*?)<\/title>/i),
    inlineStyles: firstMatch(source, /<style>([\s\S]*?)<\/style>/i),
    shellMarkup,
    stageGridMarkup,
    firstColumnMarkup,
    secondColumnMarkup,
    secondColumnFirstSectionMarkup,
    secondColumnRemainingMarkup,
    secondColumnSecondSectionMarkup,
    secondColumnTrailingMarkup
  };
}
