document.addEventListener('DOMContentLoaded', () => {
  const calendarEl = document.getElementById('calendar');
  const dayPanel = document.getElementById('day-panel');
  const dayPanelTitle = document.getElementById('day-panel-title');
  const dayPanelList = document.getElementById('day-panel-list');
  const dayPanelEmpty = document.getElementById('day-panel-empty');
  const dayPanelClose = document.getElementById('day-panel-close');
  const tooltip = document.getElementById('day-tooltip');

  let eventsByDate = {}; // 'YYYY-MM-DD' -> [event, ...] (מהאירועים שכבר נטענו ללוח)
  let currentPanelDate = null;

  // escapeHtml מגיע מ-common.js (נטען לפני קובץ זה דרך base.html)

  function formatLocalDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  function groupEventsByDate(events) {
    const map = {};
    events.forEach(ev => {
      const d = ev.start.split('T')[0];
      (map[d] = map[d] || []).push(ev);
    });
    return map;
  }

  // ---------- לוח שנה ----------
  const calendar = new FullCalendar.Calendar(calendarEl, {
    locale: 'he',
    direction: 'rtl',
    height: 'auto',
    dayMaxEvents: 3,
    headerToolbar: { start: 'prev,next today', center: 'title', end: 'dayGridMonth' },
    initialView: 'dayGridMonth',
    events: function (fetchInfo, successCallback, failureCallback) {
      fetch(`/api/calendar-events?start=${fetchInfo.startStr}&end=${fetchInfo.endStr}`)
        .then(r => r.json())
        .then(data => {
          eventsByDate = groupEventsByDate(data);
          successCallback(data);
        })
        .catch(failureCallback);
    },
    dateClick: function (info) {
      openDayPanel(info.dateStr);
    },
    dayCellDidMount: function (arg) {
      const dateStr = formatLocalDate(arg.date);
      arg.el.addEventListener('mouseenter', (e) => showTooltip(dateStr, e));
      arg.el.addEventListener('mousemove', positionTooltip);
      arg.el.addEventListener('mouseleave', hideTooltip);
    },
  });
  calendar.render();

  // ---------- hover: preview משימות היום ----------
  function showTooltip(dateStr, e) {
    const tasksOfDay = (eventsByDate[dateStr] || []).filter(ev => ev.extendedProps.type === 'task');
    if (!tasksOfDay.length) {
      hideTooltip();
      return;
    }
    tooltip.innerHTML = tasksOfDay.map(ev => `<div>• ${escapeHtml(ev.title)}</div>`).join('');
    tooltip.hidden = false;
    positionTooltip(e);
  }

  function positionTooltip(e) {
    if (tooltip.hidden) return;
    tooltip.style.top = `${e.clientY + 14}px`;
    tooltip.style.left = `${e.clientX + 14}px`;
  }

  function hideTooltip() {
    tooltip.hidden = true;
  }

  // ---------- click: פאנל ניהול משימות היום ----------
  function openDayPanel(dateStr) {
    currentPanelDate = dateStr;
    dayPanelTitle.textContent = `משימות ליום ${dateStr}`;
    dayPanel.hidden = false;
    dayPanelList.innerHTML = '';
    dayPanelEmpty.hidden = true;

    fetch(`/api/tasks-for-date/${dateStr}`)
      .then(r => r.json())
      .then(renderDayPanel)
      .catch(() => {
        dayPanelList.innerHTML = '';
        dayPanelEmpty.hidden = false;
        dayPanelEmpty.textContent = 'שגיאה בטעינת המשימות';
      });
  }

  function renderDayPanel(tasks) {
    dayPanelList.innerHTML = '';
    if (!tasks.length) {
      dayPanelEmpty.hidden = false;
      dayPanelEmpty.textContent = 'אין משימות פתוחות ביום הזה 🎉';
      return;
    }
    dayPanelEmpty.hidden = true;
    tasks.forEach(task => dayPanelList.appendChild(renderTaskRow(task)));
  }

  function renderTaskRow(task) {
    const li = document.createElement('li');
    li.className = 'task-row';
    li.dataset.taskId = task.id;

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.title = 'סימון כבוצע';
    checkbox.addEventListener('change', () => completeTask(task.id, li));

    const info = document.createElement('div');
    info.className = 'task-info';
    const timePart = task.scheduled_time ? `🕒 ${task.scheduled_time}` : '';
    const catPart = task.category_name ? `🏷️ ${escapeHtml(task.category_name)}` : '';
    info.innerHTML = `<strong>${escapeHtml(task.title)}</strong><br>` +
      `<small>${[timePart, catPart].filter(Boolean).join('  ')}</small>`;
    if (task.notes) {
      const notes = document.createElement('div');
      notes.className = 'task-notes';
      notes.textContent = task.notes;
      info.appendChild(notes);
    }

    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'icon-btn';
    editBtn.textContent = '✏️';
    editBtn.title = 'עריכה';
    editBtn.addEventListener('click', () => toggleEditForm(li, task));

    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'icon-btn';
    delBtn.textContent = '🗑️';
    delBtn.title = 'מחיקה';
    delBtn.addEventListener('click', () => deleteTask(task.id, li));

    li.append(checkbox, info, editBtn, delBtn);
    return li;
  }

  function completeTask(taskId, li) {
    fetch(`/api/tasks/${taskId}/complete`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ completed: true }),
    })
      .then(r => {
        if (!r.ok) throw new Error('complete failed');
        li.remove();
        if (!dayPanelList.children.length) {
          dayPanelEmpty.hidden = false;
          dayPanelEmpty.textContent = 'אין משימות פתוחות ביום הזה 🎉';
        }
        calendar.refetchEvents();
      })
      .catch(() => alert('שגיאה בסימון המשימה כבוצעה'));
  }

  function deleteTask(taskId, li) {
    if (!confirm('למחוק את המשימה?')) return;
    fetch(`/api/tasks/${taskId}`, { method: 'DELETE' })
      .then(r => {
        if (!r.ok) throw new Error('delete failed');
        li.remove();
        if (!dayPanelList.children.length) {
          dayPanelEmpty.hidden = false;
          dayPanelEmpty.textContent = 'אין משימות פתוחות ביום הזה 🎉';
        }
        calendar.refetchEvents();
      })
      .catch(() => alert('שגיאה במחיקת המשימה'));
  }

  function toggleEditForm(li, task) {
    const existing = li.querySelector('.task-edit-form');
    if (existing) {
      existing.remove();
      return;
    }
    const form = document.createElement('form');
    form.className = 'task-edit-form';
    form.innerHTML = `
      <input type="text" name="title" value="${escapeHtml(task.title)}" required>
      <input type="date" name="scheduled_date" value="${task.scheduled_date}" required>
      <input type="time" name="scheduled_time" value="${task.scheduled_time || ''}">
      <input type="text" name="notes" value="${escapeHtml(task.notes || '')}" placeholder="הערות">
      <button type="submit">שמור</button>
    `;
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      fetch(`/api/tasks/${task.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: fd.get('title'),
          scheduled_date: fd.get('scheduled_date'),
          scheduled_time: fd.get('scheduled_time') || null,
          notes: fd.get('notes'),
        }),
      })
        .then(r => {
          if (!r.ok) throw new Error('update failed');
          return r.json();
        })
        .then(updated => {
          calendar.refetchEvents();
          openDayPanel(updated.scheduled_date);
        })
        .catch(() => alert('שגיאה בעדכון המשימה'));
    });
    li.appendChild(form);
  }

  dayPanelClose.addEventListener('click', () => {
    dayPanel.hidden = true;
    currentPanelDate = null;
  });

  // ---------- הוספת משימה ----------
  const addTaskForm = document.getElementById('add-task-form');
  addTaskForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const title = document.getElementById('task-title').value.trim();
    const category_id = document.getElementById('task-category').value || null;
    const scheduled_date = document.getElementById('task-date').value;
    const scheduled_time = document.getElementById('task-time').value || null;
    const notes = document.getElementById('task-notes').value.trim();

    fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, category_id, scheduled_date, scheduled_time, notes }),
    })
      .then(r => {
        if (!r.ok) throw new Error('create failed');
        return r.json();
      })
      .then(() => {
        addTaskForm.reset();
        document.getElementById('task-date').value = scheduled_date;
        calendar.refetchEvents();
        if (currentPanelDate === scheduled_date) {
          openDayPanel(scheduled_date);
        }
      })
      .catch(() => alert('שגיאה בהוספת המשימה'));
  });

  // ---------- עוזר תכנון (צ'אט) ----------
  const chatForm = document.getElementById('chat-form');
  if (chatForm) {
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    let history = [];

    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const message = chatInput.value.trim();
      if (!message) return;

      appendChatMessage('user', message);
      chatInput.value = '';
      chatInput.disabled = true;

      fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history }),
      })
        .then(r => r.json())
        .then(data => {
          if (data.error) {
            appendChatMessage('assistant', `שגיאה: ${data.error}`);
            return;
          }
          history.push({ role: 'user', content: message });
          history.push({ role: 'assistant', content: data.reply });
          appendChatMessage('assistant', data.reply, data.degraded);
        })
        .catch(() => appendChatMessage('assistant', 'שגיאה בפנייה לעוזר'))
        .finally(() => {
          chatInput.disabled = false;
          chatInput.focus();
        });
    });

    function appendChatMessage(role, text, degraded) {
      const div = document.createElement('div');
      div.className = `chat-msg chat-msg-${role}`;
      div.textContent = text;
      chatMessages.appendChild(div);
      if (degraded && degraded.length) {
        const warn = document.createElement('div');
        warn.className = 'chat-degraded';
        warn.textContent = '⚠️ מקורות שלא היו זמינים הפעם: ' + degraded.join(' | ');
        chatMessages.appendChild(warn);
      }
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  }
});
