document.addEventListener('DOMContentLoaded', () => {
  const addForm = document.getElementById('add-template-form');
  const listEl = document.getElementById('template-list');
  const emptyEl = document.getElementById('template-empty');

  setupCategoryCreator({
    toggleBtn: document.getElementById('cat-creator-toggle'),
    formEl: document.getElementById('cat-creator-form'),
    inputEl: document.getElementById('cat-creator-input'),
    selects: [document.getElementById('tmpl-category')],
  });

  function loadTemplates() {
    fetch('/api/templates')
      .then(r => r.json())
      .then(renderTemplates)
      .catch(() => {
        listEl.innerHTML = '';
        emptyEl.hidden = false;
        emptyEl.textContent = 'שגיאה בטעינת התבניות';
      });
  }

  function renderTemplates(templates) {
    listEl.innerHTML = '';
    if (!templates.length) {
      emptyEl.hidden = false;
      emptyEl.textContent = 'אין תבניות עדיין';
      return;
    }
    emptyEl.hidden = true;
    templates.forEach(t => listEl.appendChild(renderTemplateRow(t)));
  }

  function renderTemplateRow(tmpl) {
    const li = document.createElement('li');
    li.className = 'task-row';

    const info = document.createElement('div');
    info.className = 'task-info';
    const status = tmpl.active ? '✅ פעיל' : '⏸️ מושבת';
    const catPart = tmpl.category_name ? escapeHtml(tmpl.category_name) : '';
    const timePart = tmpl.default_time ? `🕒 ${tmpl.default_time}` : '';
    info.innerHTML = `<strong>${escapeHtml(tmpl.title)}</strong><br>` +
      `<small>${[catPart, status].filter(Boolean).join(' · ')} ${timePart}</small>`;

    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'icon-btn';
    editBtn.textContent = '✏️';
    editBtn.title = 'עריכה';
    editBtn.addEventListener('click', () => toggleEditForm(li, tmpl));

    const toggleBtn = document.createElement('button');
    toggleBtn.type = 'button';
    toggleBtn.textContent = tmpl.active ? 'השבת' : 'הפעל';
    toggleBtn.addEventListener('click', () => {
      fetch(`/api/templates/${tmpl.id}/toggle`, { method: 'PATCH' })
        .then(r => {
          if (!r.ok) throw new Error('toggle failed');
          return r.json();
        })
        .then(() => loadTemplates())
        .catch(() => alert('שגיאה בשינוי סטטוס התבנית'));
    });

    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'icon-btn';
    delBtn.textContent = '🗑️';
    delBtn.title = 'מחיקת תבנית';
    delBtn.addEventListener('click', () => {
      if (!confirm('למחוק את התבנית?')) return;
      fetch(`/api/templates/${tmpl.id}`, { method: 'DELETE' })
        .then(r => {
          if (!r.ok) throw new Error('delete failed');
          li.remove();
        })
        .catch(() => alert('שגיאה במחיקת התבנית'));
    });

    li.append(info, editBtn, toggleBtn, delBtn);
    return li;
  }

  function toggleEditForm(li, tmpl) {
    const existing = li.querySelector('.task-edit-form');
    if (existing) {
      existing.remove();
      return;
    }
    fetchCategories().then(categories => {
      const form = document.createElement('form');
      form.className = 'task-edit-form';
      const catOptions = categories
        .map(c => `<option value="${c.id}" ${c.id === tmpl.category_id ? 'selected' : ''}>${escapeHtml(c.name)}</option>`)
        .join('');
      form.innerHTML = `
        <input type="text" name="title" value="${escapeHtml(tmpl.title)}" required>
        <select name="category_id"><option value="">(ללא קטגוריה)</option>${catOptions}</select>
        <input type="time" name="default_time" value="${tmpl.default_time || ''}">
        <button type="submit">שמור</button>
      `;
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        fetch(`/api/templates/${tmpl.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: fd.get('title'),
            category_id: fd.get('category_id') || null,
            default_time: fd.get('default_time') || null,
          }),
        })
          .then(r => {
            if (!r.ok) throw new Error('update failed');
            return r.json();
          })
          .then(() => loadTemplates())
          .catch(() => alert('שגיאה בעדכון התבנית'));
      });
      li.appendChild(form);
    });
  }

  addForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const title = document.getElementById('tmpl-title').value.trim();
    const category_id = document.getElementById('tmpl-category').value || null;
    const default_time = document.getElementById('tmpl-time').value || null;

    fetch('/api/templates', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, category_id, default_time }),
    })
      .then(r => {
        if (!r.ok) throw new Error('create failed');
        return r.json();
      })
      .then(() => {
        addForm.reset();
        loadTemplates();
      })
      .catch(() => alert('שגיאה בהוספת התבנית'));
  });

  loadTemplates();
});
