import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Landing from './Landing.jsx'
import Dashboard from './Dashboard.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/app" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  )
}
