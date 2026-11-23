(function () {
  const form = document.querySelector("[data-booking]");
  if (!form) {
    return;
  }

  const treatment = form.querySelector("[name=treatment_id]");
  const dentist = form.querySelector("[name=dentist_id]");
  const visitDate = form.querySelector("[name=visit_date]");
  const startTime = form.querySelector("[name=start_time]");
  const room = form.querySelector("[name=room_id]");
  const hint = form.querySelector("[data-slot-hint]");
  const ignoreId = form.dataset.ignoreId || "";
  const patientId = form.dataset.patientId || "";
  let preferredTime = startTime.value;
  let preferredRoom = room ? room.value : "";

  function resetSelect(select, label) {
    select.innerHTML = "";
    const option = document.createElement("option");
    option.value = "";
    option.textContent = label;
    select.appendChild(option);
  }

  function showHint(message) {
    if (hint) {
      hint.textContent = message || "";
    }
  }

  async function loadDentists() {
    const current = dentist.value;
    resetSelect(dentist, "Wybierz dentystę");
    resetSelect(startTime, "Wybierz godzinę");
    if (room) {
      resetSelect(room, "Wybierz gabinet");
    }
    showHint("");
    if (!treatment.value) {
      return;
    }

    const response = await fetch("/api/dentists?treatment_id=" + encodeURIComponent(treatment.value));
    if (!response.ok) {
      showHint("Nie udało się wczytać dentystów.");
      return;
    }
    const data = await response.json();
    (data.dentists || []).forEach((item) => {
      const option = document.createElement("option");
      option.value = String(item.id);
      option.textContent = item.name;
      if (String(item.id) === current) {
        option.selected = true;
      }
      dentist.appendChild(option);
    });
    if (dentist.value) {
      await loadSlots();
    }
  }

  async function loadSlots() {
    const current = startTime.value || preferredTime;
    resetSelect(startTime, "Wybierz godzinę");
    if (room) {
      resetSelect(room, "Wybierz gabinet");
    }
    form._slots = [];
    if (!treatment.value || !dentist.value || !visitDate.value) {
      showHint("");
      return;
    }

    const params = new URLSearchParams({
      treatment_id: treatment.value,
      dentist_id: dentist.value,
      date: visitDate.value,
    });
    if (ignoreId) {
      params.set("ignore_id", ignoreId);
    }
    if (patientId) {
      params.set("patient_id", patientId);
    }

    const response = await fetch("/api/slots?" + params.toString());
    if (!response.ok) {
      showHint("Nie udało się wczytać wolnych godzin.");
      return;
    }
    const data = await response.json();
    form._slots = data.slots || [];
    form._slots.forEach((slot) => {
      const option = document.createElement("option");
      option.value = slot.start;
      option.textContent = slot.start;
      if (slot.start === current) {
        option.selected = true;
      }
      startTime.appendChild(option);
    });
    showHint(form._slots.length ? "" : "Brak wolnych godzin w wybranym dniu.");
    if (startTime.value) {
      preferredTime = startTime.value;
    }
    fillRooms();
  }

  function fillRooms() {
    if (!room) {
      return;
    }
    const current = room.value || preferredRoom;
    resetSelect(room, "Wybierz gabinet");
    const slot = (form._slots || []).find((item) => item.start === startTime.value);
    if (!slot) {
      return;
    }
    slot.rooms.forEach((item) => {
      const option = document.createElement("option");
      option.value = String(item.id);
      option.textContent = item.name;
      if (String(item.id) === current) {
        option.selected = true;
      }
      room.appendChild(option);
    });
    if (!room.value && slot.rooms.length) {
      room.value = String(slot.rooms[0].id);
    }
    if (room.value) {
      preferredRoom = room.value;
    }
  }

  treatment.addEventListener("change", () => {
    loadDentists().catch(() => showHint("Nie udało się wczytać dentystów."));
  });
  dentist.addEventListener("change", () => {
    loadSlots().catch(() => showHint("Nie udało się wczytać wolnych godzin."));
  });
  visitDate.addEventListener("change", () => {
    loadSlots().catch(() => showHint("Nie udało się wczytać wolnych godzin."));
  });
  startTime.addEventListener("change", () => {
    preferredTime = startTime.value;
    fillRooms();
  });

  if (treatment.value) {
    loadDentists().catch(() => showHint("Nie udało się wczytać dentystów."));
  }
})();
