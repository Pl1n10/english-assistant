import { Outlet, Link } from 'react-router-dom'

export default function App() {
  return (
    <div style={{ maxWidth: 900, margin: '2rem auto', padding: '0 1rem', fontFamily: 'system-ui, sans-serif' }}>
      <header style={{ marginBottom: '1rem', display: 'flex', gap: '1rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem' }}>English Assistant</h1>
        <nav><Link to="/dashboard">Dashboard</Link></nav>
      </header>
      <Outlet />
    </div>
  )
}
