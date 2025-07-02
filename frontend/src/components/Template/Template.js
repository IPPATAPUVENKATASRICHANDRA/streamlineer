import React, { useState, useRef } from 'react';
import './Template.css';

const RESPONSE_TYPES = [
  { value: 'site', label: 'Site' },
  { value: 'date', label: 'Inspection date' },
  { value: 'person', label: 'Person' },
  { value: 'location', label: 'Inspection location' },
  { value: 'text', label: 'Text answer' },
  { value: 'number', label: 'Number' },
  { value: 'yesno', label: 'Yes/No/N/A' },
];

const APP_NAME = 'Streamlineer'; // Change to your app name

function Template() {
  const [templateTitle, setTemplateTitle] = useState('Untitled template');
  const [templateDescription, setTemplateDescription] = useState('');
  const [templateImage, setTemplateImage] = useState(null);
  const imageInputRef = useRef();
  const [titleFields, setTitleFields] = useState([
    { id: 1, label: 'Site conducte', type: 'site' },
    { id: 2, label: 'Conducted on', type: 'date' },
    { id: 3, label: 'Prepared by', type: 'person' },
    { id: 4, label: 'Location', type: 'location' },
  ]);
  const [pages, setPages] = useState([
    {
      id: 1,
      title: 'Untitled Page',
      questions: [
        { id: 1, text: '', type: 'yesno' }
      ]
    }
  ]);
  // Drag state for title fields and questions
  const [draggedFieldIdx, setDraggedFieldIdx] = useState(null);
  const [draggedQuestion, setDraggedQuestion] = useState({ pageId: null, idx: null });

  // Image upload handler
  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => setTemplateImage(ev.target.result);
      reader.readAsDataURL(file);
    }
  };

  // Title fields handlers
  const handleTitleFieldChange = (id, key, value) => {
    setTitleFields(fields => fields.map(f => f.id === id ? { ...f, [key]: value } : f));
  };
  const addTitleField = () => {
    setTitleFields(fields => [...fields, { id: Date.now(), label: '', type: 'site' }]);
  };
  const removeTitleField = (id) => {
    setTitleFields(fields => fields.filter(f => f.id !== id));
  };
  // Move title field up/down
  const moveTitleField = (idx, direction) => {
    setTitleFields(fields => {
      const newIdx = direction === 'up' ? idx - 1 : idx + 1;
      if (newIdx < 0 || newIdx >= fields.length) return fields;
      const newFields = [...fields];
      const [removed] = newFields.splice(idx, 1);
      newFields.splice(newIdx, 0, removed);
      return newFields;
    });
  };
  // Drag and drop for title fields
  const handleTitleFieldDragStart = (idx) => setDraggedFieldIdx(idx);
  const handleTitleFieldDragOver = (idx) => idx !== draggedFieldIdx;
  const handleTitleFieldDrop = (idx) => {
    if (draggedFieldIdx === null || draggedFieldIdx === idx) return;
    setTitleFields(fields => {
      const newFields = [...fields];
      const [removed] = newFields.splice(draggedFieldIdx, 1);
      newFields.splice(idx, 0, removed);
      return newFields;
    });
    setDraggedFieldIdx(null);
  };

  // Page handlers
  const addPage = () => {
    setPages(pgs => [...pgs, {
      id: Date.now(),
      title: 'Untitled Page',
      questions: [{ id: Date.now() + 1, text: '', type: 'yesno' }]
    }]);
  };
  const removePage = (id) => {
    setPages(pgs => pgs.length > 1 ? pgs.filter(p => p.id !== id) : pgs);
  };
  const handlePageTitleChange = (id, value) => {
    setPages(pgs => pgs.map(p => p.id === id ? { ...p, title: value } : p));
  };
  // Reorder pages (move up/down)
  const movePage = (id, direction) => {
    setPages(pgs => {
      const idx = pgs.findIndex(p => p.id === id);
      if (idx < 0) return pgs;
      const newIdx = direction === 'up' ? idx - 1 : idx + 1;
      if (newIdx < 0 || newIdx >= pgs.length) return pgs;
      const newPages = [...pgs];
      const [removed] = newPages.splice(idx, 1);
      newPages.splice(newIdx, 0, removed);
      return newPages;
    });
  };

  // Question handlers per page
  const addQuestion = (pageId) => {
    setPages(pgs => pgs.map(p =>
      p.id === pageId
        ? { ...p, questions: [...p.questions, { id: Date.now(), text: '', type: 'yesno' }] }
        : p
    ));
  };
  const removeQuestion = (pageId, qid) => {
    setPages(pgs => pgs.map(p =>
      p.id === pageId
        ? { ...p, questions: p.questions.length > 1 ? p.questions.filter(q => q.id !== qid) : p.questions }
        : p
    ));
  };
  const handleQuestionChange = (pageId, qid, key, value) => {
    setPages(pgs => pgs.map(p =>
      p.id === pageId
        ? { ...p, questions: p.questions.map(q => q.id === qid ? { ...q, [key]: value } : q) }
        : p
    ));
  };
  // Move question up/down
  const moveQuestion = (pageId, idx, direction) => {
    setPages(pgs => pgs.map(p => {
      if (p.id !== pageId) return p;
      const newIdx = direction === 'up' ? idx - 1 : idx + 1;
      if (newIdx < 0 || newIdx >= p.questions.length) return p;
      const newQuestions = [...p.questions];
      const [removed] = newQuestions.splice(idx, 1);
      newQuestions.splice(newIdx, 0, removed);
      return { ...p, questions: newQuestions };
    }));
  };
  // Drag and drop for questions
  const handleQuestionDragStart = (pageId, idx) => setDraggedQuestion({ pageId, idx });
  const handleQuestionDragOver = (pageId, idx) => (draggedQuestion.pageId !== pageId || draggedQuestion.idx !== idx);
  const handleQuestionDrop = (pageId, idx) => {
    if (draggedQuestion.pageId === null || draggedQuestion.idx === null) return;
    setPages(pgs => pgs.map(p => {
      if (p.id !== pageId) return p;
      const newQuestions = [...p.questions];
      const [removed] = newQuestions.splice(draggedQuestion.idx, 1);
      newQuestions.splice(idx, 0, removed);
      return { ...p, questions: newQuestions };
    }));
    setDraggedQuestion({ pageId: null, idx: null });
  };

  return (
    <div className="template-container">
      {/* App Bar */}
      <div className="app-bar">
        <span className="main-heading">Template Creation</span>
      </div>
      <div className="template-header-section">
        <div className="template-image-placeholder" onClick={() => imageInputRef.current.click()} style={{ cursor: 'pointer', position: 'relative' }}>
          {templateImage ? (
            <img src={templateImage} alt="Template" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 8 }} />
          ) : (
            <span role="img" aria-label="template">🖼️</span>
          )}
          <input
            type="file"
            accept="image/*"
            ref={imageInputRef}
            style={{ display: 'none' }}
            onChange={handleImageChange}
          />
          <span className="edit-image-label">Edit</span>
        </div>
        <div className="template-title-desc">
          <input
            className="template-title-input"
            value={templateTitle}
            onChange={e => setTemplateTitle(e.target.value)}
            placeholder="Untitled template"
            style={{ textAlign: 'left' }}
          />
          <input
            className="template-desc-input"
            value={templateDescription}
            onChange={e => setTemplateDescription(e.target.value)}
            placeholder="Add a description"
          />
        </div>
      </div>

      {/* Title Page Section */}
      <div className="section-card">
        <div className="section-header">
          <input
            className="section-title-input"
            value={templateTitle}
            onChange={e => setTemplateTitle(e.target.value)}
            placeholder="Title Page"
          />
        </div>
        <div className="section-description">
          The Title Page is the first page of your inspection report. You can customize the Title Page below.
        </div>
        <div className="fields-table">
          <div className="fields-table-header">
            <span>Question</span>
            <span>Type of response</span>
            <span></span>
          </div>
          {titleFields.map((field, idx) => (
            <div
              className={`fields-table-row draggable-row${draggedFieldIdx === idx ? ' dragging' : ''}`}
              key={field.id}
              draggable
              onDragStart={() => handleTitleFieldDragStart(idx)}
              onDragOver={e => { e.preventDefault(); if (handleTitleFieldDragOver(idx)) e.currentTarget.classList.add('drag-over'); }}
              onDragLeave={e => e.currentTarget.classList.remove('drag-over')}
              onDrop={e => { handleTitleFieldDrop(idx); e.currentTarget.classList.remove('drag-over'); }}
            >
              <input
                className="field-label-input"
                value={field.label}
                onChange={e => handleTitleFieldChange(field.id, 'label', e.target.value)}
                placeholder="Field label"
              />
              <select
                className="field-type-select"
                value={field.type}
                onChange={e => handleTitleFieldChange(field.id, 'type', e.target.value)}
              >
                {RESPONSE_TYPES.filter(rt => ['site','date','person','location','text','number'].includes(rt.value)).map(rt => (
                  <option key={rt.value} value={rt.value}>{rt.label}</option>
                ))}
              </select>
              <div className="row-actions">
                <button className="move-btn" onClick={() => moveTitleField(idx, 'up')} disabled={idx === 0} title="Move up">↑</button>
                <button className="move-btn" onClick={() => moveTitleField(idx, 'down')} disabled={idx === titleFields.length - 1} title="Move down">↓</button>
                <button className="remove-btn" onClick={() => removeTitleField(field.id)} disabled={titleFields.length <= 1}>×</button>
              </div>
            </div>
          ))}
          <button className="add-btn" onClick={addTitleField}>+ Add new</button>
        </div>
      </div>

      {/* Pages Section */}
      {pages.map((page, pageIdx) => (
        <div className="section-card" key={page.id}>
          <div className="section-header">
            <input
              className="section-title-input"
              value={page.title}
              onChange={e => handlePageTitleChange(page.id, e.target.value)}
              placeholder="Untitled Page"
            />
            <div className="page-actions">
              <button className="move-btn" onClick={() => movePage(page.id, 'up')} disabled={pageIdx === 0} title="Move up">↑</button>
              <button className="move-btn" onClick={() => movePage(page.id, 'down')} disabled={pageIdx === pages.length - 1} title="Move down">↓</button>
              <button className="remove-btn" onClick={() => removePage(page.id)} disabled={pages.length <= 1}>×</button>
            </div>
          </div>
          <div className="section-description">
            This is where you add your inspection questions and how you want them answered. E.g. "Is the floor clean?"
          </div>
          <div className="fields-table">
            <div className="fields-table-header">
              <span>Question</span>
              <span>Type of response</span>
              <span></span>
            </div>
            {page.questions.map((q, idx) => (
              <div
                className={`fields-table-row draggable-row${draggedQuestion.pageId === page.id && draggedQuestion.idx === idx ? ' dragging' : ''}`}
                key={q.id}
                draggable
                onDragStart={() => handleQuestionDragStart(page.id, idx)}
                onDragOver={e => { e.preventDefault(); if (handleQuestionDragOver(page.id, idx)) e.currentTarget.classList.add('drag-over'); }}
                onDragLeave={e => e.currentTarget.classList.remove('drag-over')}
                onDrop={e => { handleQuestionDrop(page.id, idx); e.currentTarget.classList.remove('drag-over'); }}
              >
                <input
                  className="field-label-input"
                  value={q.text}
                  onChange={e => handleQuestionChange(page.id, q.id, 'text', e.target.value)}
                  placeholder="Type question"
                />
                <select
                  className="field-type-select"
                  value={q.type}
                  onChange={e => handleQuestionChange(page.id, q.id, 'type', e.target.value)}
                >
                  {RESPONSE_TYPES.map(rt => (
                    <option key={rt.value} value={rt.value}>{rt.label}</option>
                  ))}
                </select>
                <div className="row-actions">
                  <button className="move-btn" onClick={() => moveQuestion(page.id, idx, 'up')} disabled={idx === 0} title="Move up">↑</button>
                  <button className="move-btn" onClick={() => moveQuestion(page.id, idx, 'down')} disabled={idx === page.questions.length - 1} title="Move down">↓</button>
                  <button className="remove-btn" onClick={() => removeQuestion(page.id, q.id)} disabled={page.questions.length <= 1}>×</button>
                </div>
              </div>
            ))}
            <button className="add-btn" onClick={() => addQuestion(page.id)}>+ Add new</button>
          </div>
        </div>
      ))}
      <button className="add-page-btn" onClick={addPage}>+ Add Page</button>
    </div>
  );
}

export default Template; 