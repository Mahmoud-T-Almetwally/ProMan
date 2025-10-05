import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';

import UserAuthRoutes from './modules/UserAuth/routes';
import ProjectsRoutes from './modules/Projects/routes';
import TasksRoutes from './modules/Tasks/routes';
import ChatRoutes from './modules/Chat/routes';


const AppLayout = () => (
  <div>
    <header>
      <nav>
        <Link to="/projects">Projects</Link> | <Link to="/tasks">Tasks</Link> | <Link to="/chat">Chat</Link> | <Link to="/login">Login</Link>
      </nav>
    </header>
    <main>
      <Routes>
        <Route path="/auth/*" element={<UserAuthRoutes />} />
        <Route path="/projects/*" element={<ProjectsRoutes />} />
        <Route path="/tasks/*" element={<TasksRoutes />} />
        <Route path="/chat/*" element={<ChatRoutes />} />
        <Route path="/" element={<h2>Welcome to your Project Management App!</h2>} />
      </Routes>
    </main>
  </div>
);


function App() {
  return (
    <Router>
      <AppLayout />
    </Router>
  );
}

export default App;