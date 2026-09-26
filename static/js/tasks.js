document.addEventListener('DOMContentLoaded', () => {
  const addForm = document.getElementById('add-task-form');
  const filterForm = document.getElementById('filter-form');
  const filterClearBtn = document.getElementById('filter-clear');
  const tasksByDateEl = document.getElementById('tasks-by-date');
  const tasksEmptyEl = document.getElementById('tasks-empty');
  const tasksCountEl = document.getElementById('tasks-count');

  setupCategoryCreator({
    toggleBtn: document.getElementById('cat-creator-toggle'),
    formEl: document.getElementById('cat-creator-form'),
    inputEl: document.getElementById('cat-creator-input'),
    selects: [document.getElementById('task-category'), document.getElementById('filter-category')],
  });

  function currentFilters() {
    const params = new URLSearchParams();
    const dateFrom = document.getElementById('filter-date-from').value;
    const dateTo = document.getElementById('filter-date-to').value;
    const categoryId = document.getElementById('filter-category').value;
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    if (categoryId) params.set('category_id', categoryId);
    if (document.getElementById('filter-completed').checked) params.set('include_completed', '1');
    return params;
  }

  function loadTasks() {
    fetch(`/api/tasks?${currentFilters().toString()}`)
      .then(r => r.json())
      .then(renderTasks)
      .catch(() => {
        tasksByDateEl.innerHTML = '';
        tasksEmptyEl.hidden = false;
        tasksEmptyEl.textContent = 'שגיאה בטעינת המשימות';
      });
  }

  function renderTasks(tasks) {
    const showingCompleted = document.getElementById('filter-completed').checked;
    tasksCountEl.textContent = showingCompleted
      ? `משימות שהושלמו (${tasks.length})`
      : `משימות פתוחות (${tasks.length})`;
    tasksByDateEl.innerHTML = '';
    if (!tasks.length) {
      tasksEmptyEl.hidden = false;
      tasksEmptyEl.textContent = showingCompleted ? 'אין משימות שהושלמו' : 'לא נמצאו משימות';
      return;
    }
    tasksEmptyEl.hidden = true;

    const grouped = {};
    tasks.forEach(t => (grouped[t.scheduled_date] = grouped[t.scheduled_date] || []).push(t));
    Object.keys(grouped).sort().forEach(dateKey => {
      const heading = document.createElement('h3');
      heading.textContent = dateKey;
      tasksByDateEl.appendChild(heading);

      const list = document.createElement('ul');
      list.className = 'task-list';
      grouped[dateKey].forEach(task => list.appendChild(renderTaskRow(task)));
      tasksByDateEl.appendChild(list);
    });
  }

  function renderTaskRow(task) {
    const li = document.createElement('li');
    li.className = 'task-row';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = task.completed;
    checkbox.title = 'בוצע';
    checkbox.addEventListener('change', () => {
      fetch(`/api/tasks/${task.id}/complete`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed: checkbox.checked }),
      })
        .then(r => {
          if (!r.ok) throw new Error('toggle failed');
          return r.json();
        })
        .then(() => loadTasks())
        .catch(() => {
          checkbox.checked = task.completed;
          alert('שגיאה בעדכון סטטוס המשימה');
        });
    });

    const info = document.createElement('div');
    info.className = 'task-info';
    const title = document.createElement('strong');
    title.innerHTML = task.completed ? `<s>${escapeHtml(task.title)}</s>` : escapeHtml(task.title);
    const timePart = task.scheduled_time ? `🕒 ${task.scheduled_time}` : '';
    const catPart = task.category_name ? `🏷️ ${escapeHtml(task.category_name)}` : '';
    const small = document.createElement('small');
    small.textContent = [timePart, catPart].filter(Boolean).join('  ');
    info.append(title, document.createElement('br'), small);
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
    delBtn.addEventListener('click', () => {
      if (!confirm('למחוק את המשימה?')) return;
      fetch(`/api/tasks/${task.id}`, { method: 'DELETE' })
        .then(r => {
          if (!r.ok) throw new Error('delete failed');
          li.remove();
        })
        .catch(() => alert('שגיאה במחיקת המשימה'));
    });

    li.append(checkbox, info, editBtn, delBtn);
    return li;
  }

  function toggleEditForm(li, task) {
    const existing = li.querySelector('.task-edit-form');
    if (existing) {
      existing.remove();
      return;
    }
    fetchCategories().then(categories => {
      const form = document.createElement('form');
      form.className = 'task-edit-form';
      const catOptions = categories
        .map(c => `<option value="${c.id}" ${c.id === task.category_id ? 'selected' : ''}>${escapeHtml(c.name)}</option>`)
        .join('');
      form.innerHTML = `
        <input type="text" name="title" value="${escapeHtml(task.title)}" required>
        <select name="category_id"><option value="">(ללא קטגוריה)</option>${catOptions}</select>
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
            category_id: fd.get('category_id') || null,
            scheduled_date: fd.get('scheduled_date'),
            scheduled_time: fd.get('scheduled_time') || null,
            notes: fd.get('notes'),
          }),
        })
          .then(r => {
            if (!r.ok) throw new Error('update failed');
            return r.json();
          })
          .then(() => loadTasks())
          .catch(() => alert('שגיאה בעדכון המשימה'));
      });
      li.appendChild(form);
    });
  }

  addForm.addEventListener('submit', (e) => {
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
        addForm.reset();
        document.getElementById('task-date').value = scheduled_date;
        loadTasks();
      })
      .catch(() => alert('שגיאה בהוספת המשימה'));
  });

  filterForm.addEventListener('submit', (e) => {
    e.preventDefault();
    loadTasks();
  });

  document.getElementById('filter-completed').addEventListener('change', loadTasks);

  filterClearBtn.addEventListener('click', () => {
    filterForm.reset();
    loadTasks();
  });

  loadTasks();
});
