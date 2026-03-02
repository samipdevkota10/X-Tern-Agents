import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage, CaseListPage, CaseDetailPage } from './pages';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/cases" element={<CaseListPage />} />
          <Route path="/cases/:id" element={<CaseDetailPage />} />
          <Route path="/" element={<Navigate to="/cases" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
