import { Link } from 'react-router-dom'

export default function Dashboard() {
  return (
    <div>
      <p>Dashboard placeholder</p>
      <p><Link to="/conversations/1">Apri conversazione #1</Link></p>
    </div>
  )
}
