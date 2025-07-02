import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import LandingPage from './components/LandingPage/LandingPage';
import SignUp from './components/SignUp/SignUp';
import Login from './components/SignUp/Login';
import Dashboard from './components/Dashboard/Dashboard';
import Template from './components/Template/Template';
import Schedule from './components/Schedule/Schedule';
import Navigation from './components/Navigation/Navigation';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Navigation />
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="/login" element={<Login />} />
          <Route path="/dashboard" element={<Dashboard />} />
          {/* <Route path="/template" element={<Template />} /> */}
          <Route path="/schedule" element={<Schedule />} />
          <Route path="/template" element={<Template />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
