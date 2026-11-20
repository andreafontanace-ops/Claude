// Suggerimenti dei marchi nell'avvio guidato: un tocco aggiunge ai concorrenti, due tocchi ai propri marchi.
document.querySelectorAll(".chip[data-target]").forEach((chip) => {
  let taps = 0;
  let timer;
  chip.addEventListener("click", () => {
    taps += 1;
    clearTimeout(timer);
    timer = setTimeout(() => {
      const field = document.getElementById(taps > 1 ? chip.dataset.own : chip.dataset.target);
      const names = field.value.split(",").map((s) => s.trim()).filter(Boolean);
      if (!names.includes(chip.textContent)) names.push(chip.textContent);
      field.value = names.join(", ");
      chip.classList.add("on");
      taps = 0;
    }, 250);
  });
});
