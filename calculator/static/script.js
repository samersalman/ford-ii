// Minimal client-side sanity hint for GCS. No frameworks; server is source of truth.
(function () {
  var gcs = document.getElementById("gcs");
  if (!gcs) return;
  gcs.addEventListener("blur", function () {
    var v = parseFloat(gcs.value);
    if (!isNaN(v) && (v < 3 || v > 15)) {
      gcs.setCustomValidity("GCS must be between 3 and 15.");
      gcs.reportValidity();
    } else {
      gcs.setCustomValidity("");
    }
  });
})();
