function perbaruiProgress() {
  const form = document.getElementById("form-tes");
  if (!form) return;

  const totalPertanyaan = form.querySelectorAll(".question-card").length;
  const kelompokTerjawab = new Set();

  form.querySelectorAll('input[type="radio"]:checked').forEach((el) => {
    kelompokTerjawab.add(el.name);
  });

  const terjawab = kelompokTerjawab.size;
  const persen = totalPertanyaan ? Math.round((terjawab / totalPertanyaan) * 100) : 0;

  const bar = document.getElementById("progress-bar");
  if (bar) bar.style.width = persen + "%";

  const teks = document.getElementById("progress-text");
  if (teks) teks.textContent = `${terjawab} / ${totalPertanyaan} pertanyaan terjawab`;
}

/* ---------------- Wizard: satu tipe kepribadian per layar ---------------- */
function initWizard() {
  const form = document.getElementById("form-tes");
  const steps = form ? Array.from(form.querySelectorAll(".step")) : [];
  if (!form || steps.length === 0) return;

  const dots = Array.from(document.querySelectorAll(".wizard-dot"));
  const btnPrev = document.getElementById("btn-prev");
  const btnNext = document.getElementById("btn-next");
  const btnFinal = document.getElementById("btn-final");
  const stepText = document.getElementById("wizard-step-text");
  const warning = document.getElementById("wizard-warning");

  let current = 0;
  let maxReached = 0;

  function namesInStep(stepEl) {
    const names = new Set();
    stepEl.querySelectorAll('input[type="radio"]').forEach((el) => names.add(el.name));
    return Array.from(names);
  }

  function stepAnswered(index) {
    return namesInStep(steps[index]).every(
      (name) => form.querySelector(`input[name="${name}"]:checked`) !== null
    );
  }

  function markUnanswered(stepEl) {
    namesInStep(stepEl).forEach((name) => {
      const answered = form.querySelector(`input[name="${name}"]:checked`) !== null;
      const card = stepEl.querySelector(`input[name="${name}"]`).closest(".question-card");
      card.classList.toggle("question-card-missing", !answered);
    });
  }

  function goTo(index, shouldScroll = true) {
    steps[current].classList.remove("step-active");
    current = index;
    steps[current].classList.add("step-active");
    if (index > maxReached) maxReached = index;

    dots.forEach((dot, i) => {
      dot.classList.toggle("wizard-dot-active", i === current);
      dot.classList.toggle("wizard-dot-done", i < current || (i <= maxReached && i !== current));
      dot.disabled = i > maxReached;
    });

    const isLast = current === steps.length - 1;
    btnPrev.disabled = current === 0;
    btnNext.hidden = isLast;
    btnFinal.hidden = !isLast;
    stepText.textContent = `Bagian ${current + 1} dari ${steps.length}`;
    warning.hidden = true;

    if (shouldScroll) {
      const header = document.querySelector(".navbar");
      const offset = header ? header.offsetHeight + 10 : 0;
      const top = steps[current].getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: "smooth" });
    }
  }

  btnNext.addEventListener("click", () => {
    if (!stepAnswered(current)) {
      markUnanswered(steps[current]);
      warning.hidden = false;
      return;
    }
    if (current < steps.length - 1) goTo(current + 1);
  });

  btnPrev.addEventListener("click", () => {
    if (current > 0) goTo(current - 1);
  });

  dots.forEach((dot, i) => {
    dot.addEventListener("click", () => {
      if (!dot.disabled) goTo(i);
    });
  });

  form.addEventListener("submit", (e) => {
    if (!stepAnswered(current)) {
      e.preventDefault();
      markUnanswered(steps[current]);
      warning.hidden = false;
    }
  });

  // Jangan melakukan auto-scroll saat halaman tes pertama kali dibuka.
  // Petunjuk pengerjaan harus tetap terlihat dari posisi paling atas.
  window.scrollTo({ top: 0, behavior: "auto" });
  goTo(0, false);
}

document.addEventListener("DOMContentLoaded", () => {
  perbaruiProgress();
  initWizard();
});
