// פונקציות עזר משותפות לכל עמודי האתר (נטען לפני JS ספציפי-לעמוד ב-base.html).

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s == null ? '' : s;
  return div.innerHTML;
}

function populateCategorySelect(selectEl, categories, { includeEmptyOption = true } = {}) {
  selectEl.innerHTML = '';
  if (includeEmptyOption) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = '(ללא קטגוריה)';
    selectEl.appendChild(opt);
  }
  categories.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = c.name;
    selectEl.appendChild(opt);
  });
}

function fetchCategories() {
  return fetch('/api/categories').then(r => r.json());
}

// מחבר טופס מיני ("+ קטגוריה חדשה") ל-select נתון: לחיצה על הכפתור פותחת
// שדה טקסט + אישור, ולאחר יצירה מרעננת את ה-select (או כמה selects) שהועברו.
function setupCategoryCreator({ toggleBtn, formEl, inputEl, selects }) {
  toggleBtn.addEventListener('click', () => {
    formEl.hidden = !formEl.hidden;
    if (!formEl.hidden) inputEl.focus();
  });

  formEl.addEventListener('submit', (e) => {
    e.preventDefault();
    const name = inputEl.value.trim();
    if (!name) return;
    fetch('/api/categories', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
      .then(r => {
        if (!r.ok) throw new Error('create category failed');
        return r.json();
      })
      .then(() => fetchCategories())
      .then(categories => {
        selects.forEach(sel => {
          const current = sel.value;
          populateCategorySelect(sel, categories);
          if ([...sel.options].some(o => o.value === current)) sel.value = current;
        });
        inputEl.value = '';
        formEl.hidden = true;
      })
      .catch(() => alert('שגיאה ביצירת הקטגוריה'));
  });
}
