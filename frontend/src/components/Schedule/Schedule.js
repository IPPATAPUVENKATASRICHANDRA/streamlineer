import React, { useState } from 'react';
import './Schedule.css';

function Schedule() {
  const [schedules, setSchedules] = useState([
    {
      id: 1,
      templateName: 'Safety Inspection Template',
      inspectorName: 'John Smith',
      inspectorEmail: 'john.smith@company.com',
      location: 'Building A - Floor 3',
      scheduledDate: '2024-01-20',
      scheduledTime: '09:00',
      status: 'scheduled',
      priority: 'high',
      notes: 'Focus on electrical safety and fire exits',
      createdBy: 'Manager',
      createdAt: '2024-01-15'
    },
    {
      id: 2,
      templateName: 'Equipment Maintenance Template',
      inspectorName: 'Sarah Johnson',
      inspectorEmail: 'sarah.johnson@company.com',
      location: 'Warehouse B',
      scheduledDate: '2024-01-22',
      scheduledTime: '14:00',
      status: 'in-progress',
      priority: 'medium',
      notes: 'Check all forklifts and lifting equipment',
      createdBy: 'Manager',
      createdAt: '2024-01-16'
    }
  ]);

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newSchedule, setNewSchedule] = useState({
    templateName: '',
    inspectorName: '',
    inspectorEmail: '',
    location: '',
    scheduledDate: '',
    scheduledTime: '',
    priority: 'medium',
    notes: ''
  });

  const availableTemplates = [
    'Safety Inspection Template',
    'Equipment Maintenance Template',
    'Fire Safety Template',
    'Environmental Compliance Template'
  ];

  const availableInspectors = [
    { name: 'John Smith', email: 'john.smith@company.com' },
    { name: 'Sarah Johnson', email: 'sarah.johnson@company.com' },
    { name: 'Mike Davis', email: 'mike.davis@company.com' },
    { name: 'Lisa Wilson', email: 'lisa.wilson@company.com' }
  ];

  const handleCreateSchedule = (e) => {
    e.preventDefault();
    const schedule = {
      id: schedules.length + 1,
      ...newSchedule,
      status: 'scheduled',
      createdBy: 'Manager',
      createdAt: new Date().toISOString().split('T')[0]
    };
    setSchedules(prev => [...prev, schedule]);
    setNewSchedule({
      templateName: '',
      inspectorName: '',
      inspectorEmail: '',
      location: '',
      scheduledDate: '',
      scheduledTime: '',
      priority: 'medium',
      notes: ''
    });
    setShowCreateForm(false);
  };

  const updateScheduleStatus = (id, newStatus) => {
    setSchedules(prev => 
      prev.map(schedule => 
        schedule.id === id ? { ...schedule, status: newStatus } : schedule
      )
    );
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'scheduled': return '#2196f3';
      case 'in-progress': return '#ff9800';
      case 'completed': return '#4caf50';
      case 'cancelled': return '#f44336';
      default: return '#666';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return '#f44336';
      case 'medium': return '#ff9800';
      case 'low': return '#4caf50';
      default: return '#666';
    }
  };

  return (
    <div className="schedule-container">
      <div className="schedule-header">
        <h1 className="schedule-title">Schedule Management</h1>
        <p className="schedule-subtitle">Assign templates to inspectors and manage inspection schedules</p>
        <button 
          className="create-schedule-btn"
          onClick={() => setShowCreateForm(true)}
        >
          Create New Schedule
        </button>
      </div>

      {showCreateForm && (
        <div className="schedule-form-overlay">
          <div className="schedule-form-container">
            <div className="schedule-form-header">
              <h2>Create New Schedule</h2>
              <button 
                className="close-btn"
                onClick={() => setShowCreateForm(false)}
              >
                ×
              </button>
            </div>
            <form onSubmit={handleCreateSchedule} className="schedule-form">
              <div className="form-group">
                <label htmlFor="template-name">Template</label>
                <select
                  id="template-name"
                  value={newSchedule.templateName}
                  onChange={(e) => setNewSchedule(prev => ({ ...prev, templateName: e.target.value }))}
                  required
                >
                  <option value="">Select a template</option>
                  {availableTemplates.map(template => (
                    <option key={template} value={template}>{template}</option>
                  ))}
                </select>
              </div>
              
              <div className="form-group">
                <label htmlFor="inspector-name">Inspector</label>
                <select
                  id="inspector-name"
                  value={newSchedule.inspectorName}
                  onChange={(e) => {
                    const inspector = availableInspectors.find(i => i.name === e.target.value);
                    setNewSchedule(prev => ({ 
                      ...prev, 
                      inspectorName: e.target.value,
                      inspectorEmail: inspector ? inspector.email : ''
                    }));
                  }}
                  required
                >
                  <option value="">Select an inspector</option>
                  {availableInspectors.map(inspector => (
                    <option key={inspector.name} value={inspector.name}>{inspector.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="location">Location</label>
                <input
                  type="text"
                  id="location"
                  value={newSchedule.location}
                  onChange={(e) => setNewSchedule(prev => ({ ...prev, location: e.target.value }))}
                  placeholder="e.g., Building A - Floor 3"
                  required
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="scheduled-date">Date</label>
                  <input
                    type="date"
                    id="scheduled-date"
                    value={newSchedule.scheduledDate}
                    onChange={(e) => setNewSchedule(prev => ({ ...prev, scheduledDate: e.target.value }))}
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="scheduled-time">Time</label>
                  <input
                    type="time"
                    id="scheduled-time"
                    value={newSchedule.scheduledTime}
                    onChange={(e) => setNewSchedule(prev => ({ ...prev, scheduledTime: e.target.value }))}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="priority">Priority</label>
                <select
                  id="priority"
                  value={newSchedule.priority}
                  onChange={(e) => setNewSchedule(prev => ({ ...prev, priority: e.target.value }))}
                  required
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="notes">Notes</label>
                <textarea
                  id="notes"
                  value={newSchedule.notes}
                  onChange={(e) => setNewSchedule(prev => ({ ...prev, notes: e.target.value }))}
                  placeholder="Additional instructions or notes for the inspector"
                />
              </div>

              <div className="form-actions">
                <button type="button" className="cancel-btn" onClick={() => setShowCreateForm(false)}>
                  Cancel
                </button>
                <button type="submit" className="submit-btn">
                  Create Schedule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="schedules-grid">
        {schedules.map(schedule => (
          <div key={schedule.id} className="schedule-card">
            <div className="schedule-card-header">
              <h3>{schedule.templateName}</h3>
              <div className="schedule-badges">
                <span 
                  className="status-badge"
                  style={{ backgroundColor: getStatusColor(schedule.status) + '20', color: getStatusColor(schedule.status) }}
                >
                  {schedule.status}
                </span>
                <span 
                  className="priority-badge"
                  style={{ backgroundColor: getPriorityColor(schedule.priority) + '20', color: getPriorityColor(schedule.priority) }}
                >
                  {schedule.priority}
                </span>
              </div>
            </div>
            
            <div className="schedule-details">
              <div className="detail-row">
                <span className="detail-label">Inspector:</span>
                <span className="detail-value">{schedule.inspectorName}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Email:</span>
                <span className="detail-value">{schedule.inspectorEmail}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Location:</span>
                <span className="detail-value">{schedule.location}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Date & Time:</span>
                <span className="detail-value">
                  {new Date(schedule.scheduledDate).toLocaleDateString()} at {schedule.scheduledTime}
                </span>
              </div>
              {schedule.notes && (
                <div className="detail-row">
                  <span className="detail-label">Notes:</span>
                  <span className="detail-value">{schedule.notes}</span>
                </div>
              )}
            </div>

            <div className="schedule-meta">
              <span>Created by: {schedule.createdBy}</span>
              <span>Date: {schedule.createdAt}</span>
            </div>

            <div className="schedule-actions">
              <select
                className="status-select"
                value={schedule.status}
                onChange={(e) => updateScheduleStatus(schedule.id, e.target.value)}
              >
                <option value="scheduled">Scheduled</option>
                <option value="in-progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
              <button className="edit-btn">Edit</button>
              <button className="view-btn">View Details</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Schedule; 