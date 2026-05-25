(function () {
  var form = document.getElementById("calculator-form");
  var resultPanel = document.getElementById("result-panel");
  var status = document.getElementById("form-status");
  var submitButton = document.getElementById("submit-button");
  var riskGroupsNode = document.getElementById("risk-groups-data");
  var riskGroups = [];

  if (!form || !resultPanel || !status || !submitButton || !riskGroupsNode) {
    return;
  }

  try {
    riskGroups = JSON.parse(riskGroupsNode.textContent || "[]");
  } catch (error) {
    riskGroups = [];
  }

  attachSanityChecks();

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    clearStatus();

    if (!form.reportValidity()) {
      return;
    }

    var payload = Object.fromEntries(new FormData(form).entries());
    setBusy(true);
    status.textContent = "Calculating FORD-II score...";

    window.fetch(form.action, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify(payload)
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Request failed");
        }
        return response.json();
      })
      .then(function (result) {
        renderResult(result);
        status.textContent = "Result updated.";
        clearError();
        resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
      })
      .catch(function () {
        status.textContent = "Unable to calculate the score right now. Try again.";
        status.classList.add("is-error");
      })
      .finally(function () {
        setBusy(false);
      });
  });

  form.addEventListener("reset", function () {
    window.setTimeout(function () {
      renderEmptyState();
      status.textContent = "Form cleared.";
      clearError();
    }, 0);
  });

  function attachSanityChecks() {
    var gcs = document.getElementById("gcs");
    if (!gcs) {
      return;
    }

    gcs.addEventListener("blur", function () {
      var value = parseFloat(gcs.value);
      if (!isNaN(value) && (value < 3 || value > 15)) {
        gcs.setCustomValidity("GCS must be between 3 and 15.");
        gcs.reportValidity();
      } else {
        gcs.setCustomValidity("");
      }
    });
  }

  function renderResult(result) {
    var riskClass = getRiskClass(result.risk_group && result.risk_group.label);
    var activeContributors = Array.isArray(result.active_contributions) ? result.active_contributions : [];
    var allContributions = Array.isArray(result.all_contributions) ? result.all_contributions : [];

    resultPanel.dataset.hasResult = "true";
    resultPanel.classList.remove("result-stack-empty");
    resultPanel.innerHTML = [
      '<section class="result-card card ' + riskClass + '">',
      '  <div class="result-card-header">',
      '    <div>',
      '      <p class="section-kicker">Current result</p>',
      '      <h2>Risk summary</h2>',
      '    </div>',
      '    <span class="risk-badge">' + escapeHtml(result.risk_group.label) + '</span>',
      '  </div>',
      '  <div class="metric-grid">',
      buildMetricTile("FORD-II score", String(result.score), "Displayed score (" + result.score_limits.min + "-" + result.score_limits.max + ")", true),
      buildMetricTile("Raw score", String(result.raw_score), result.score_was_clipped ? ("Clipped to " + result.score + " for risk estimation") : "No clipping applied"),
      buildMetricTile("Predicted non-home discharge", result.probability_pct + "%", "Model-predicted probability"),
      buildMetricTile(
        "Observed event rate",
        result.risk_group.event_rate_pct + "%",
        escapeHtml(result.risk_group.label) + " group, 95% CI " + result.risk_group.ci_lo_pct + "-" + result.risk_group.ci_hi_pct + "%"
      ),
      "  </div>",
      "</section>",
      '<section class="card">',
      '  <div class="section-heading">',
      '    <div>',
      '      <p class="section-kicker">Transparency</p>',
      '      <h2>Active contributors</h2>',
      '    </div>',
      '    <p class="section-copy">Rules that were met for the current input.</p>',
      '  </div>',
      '  <div class="contributors-list">' + buildActiveContributors(activeContributors, result.score) + "</div>",
      "</section>",
      '<section class="card">',
      '  <div class="section-heading">',
      '    <div>',
      '      <p class="section-kicker">Reference</p>',
      '      <h2>Risk groups</h2>',
      '    </div>',
      '    <p class="section-copy">Observed NTDB event rates for each score band.</p>',
      '  </div>',
      '  <div class="table-wrap">' + buildRiskGroupTable(result.risk_group.label) + "</div>",
      "</section>",
      '<section class="card">',
      '  <div class="section-heading">',
      '    <div>',
      '      <p class="section-kicker">Modeled rules</p>',
      '      <h2>Full breakdown</h2>',
      '    </div>',
      '    <p class="section-copy">All FORD-II rules, including those not triggered.</p>',
      '  </div>',
      '  <div class="table-wrap">' + buildBreakdownTable(allContributions) + "</div>",
      "</section>"
    ].join("");
  }

  function renderEmptyState() {
    resultPanel.dataset.hasResult = "false";
    resultPanel.classList.add("result-stack-empty");
    resultPanel.innerHTML = [
      '<section class="card empty-result-card">',
      '  <div class="section-heading">',
      '    <div>',
      '      <p class="section-kicker">Ready to calculate</p>',
      '      <h2>Enter patient factors</h2>',
      '    </div>',
      '    <p class="section-copy">Results will appear here after you press <strong>Calculate FORD-II</strong>.</p>',
      '  </div>',
      '  <ul class="empty-checklist">',
      '    <li>Review clipped score, raw score, and predicted probability.</li>',
      '    <li>See the matching NTDB risk group and observed event rate.</li>',
      '    <li>Inspect active contributors and the full rule-by-rule breakdown.</li>',
      '  </ul>',
      '</section>'
    ].join("");
  }

  function buildMetricTile(label, value, footnote, isScore) {
    return [
      '<article class="metric-tile' + (isScore ? " metric-score" : "") + '">',
      '  <span class="metric-label">' + escapeHtml(label) + '</span>',
      '  <strong>' + escapeHtml(value) + '</strong>',
      '  <span class="metric-footnote">' + footnote + '</span>',
      '</article>'
    ].join("");
  }

  function buildActiveContributors(items, score) {
    if (!items.length) {
      return '<p class="empty-state">No modeled predictors were triggered. The displayed score remains ' + escapeHtml(String(score)) + ".</p>";
    }

    return items.map(function (item) {
      return [
        '<article class="contributor contributor-active">',
        '  <div>',
        '    <h3>' + escapeHtml(item.label) + '</h3>',
        '    <p>' + escapeHtml(item.condition) + '</p>',
        '  </div>',
        '  <strong>' + escapeHtml(item.signed_points) + '</strong>',
        '</article>'
      ].join("");
    }).join("");
  }

  function buildRiskGroupTable(currentLabel) {
    return [
      '<table class="data-table">',
      '  <thead>',
      '    <tr>',
      '      <th>Group</th>',
      '      <th>Score range</th>',
      '      <th>Observed event rate</th>',
      '      <th>95% CI</th>',
      '    </tr>',
      '  </thead>',
      '  <tbody>',
      riskGroups.map(function (group) {
        return [
          '<tr class="' + (group.label === currentLabel ? "is-current" : "") + '">',
          '  <td>' + escapeHtml(group.label) + '</td>',
          '  <td>' + escapeHtml(group.score_range) + '</td>',
          '  <td>' + escapeHtml(String(group.event_rate_pct)) + '%</td>',
          '  <td>' + escapeHtml(String(group.ci_lo_pct)) + "-" + escapeHtml(String(group.ci_hi_pct)) + '%</td>',
          '</tr>'
        ].join("");
      }).join(""),
      '  </tbody>',
      '</table>'
    ].join("");
  }

  function buildBreakdownTable(items) {
    return [
      '<table class="data-table breakdown-table">',
      '  <thead>',
      '    <tr>',
      '      <th>Predictor</th>',
      '      <th>Condition</th>',
      '      <th>Status</th>',
      '      <th>Points</th>',
      '    </tr>',
      '  </thead>',
      '  <tbody>',
      items.map(function (item) {
        return [
          '<tr class="' + (item.met ? "is-active" : "") + '">',
          '  <td>' + escapeHtml(item.label) + '</td>',
          '  <td>' + escapeHtml(item.condition) + '</td>',
          '  <td>' + (item.met ? "Met" : "Not met") + '</td>',
          '  <td>' + escapeHtml(item.signed_points) + '</td>',
          '</tr>'
        ].join("");
      }).join(""),
      '  </tbody>',
      '</table>'
    ].join("");
  }

  function clearStatus() {
    status.textContent = "";
    clearError();
  }

  function clearError() {
    status.classList.remove("is-error");
  }

  function setBusy(isBusy) {
    resultPanel.setAttribute("aria-busy", isBusy ? "true" : "false");
    submitButton.disabled = isBusy;
  }

  function getRiskClass(label) {
    switch (label) {
      case "Low":
        return "risk-low";
      case "Low-Mod":
        return "risk-low-mod";
      case "Mod-High":
        return "risk-mod-high";
      case "High":
        return "risk-high";
      default:
        return "risk-low";
    }
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }
})();
