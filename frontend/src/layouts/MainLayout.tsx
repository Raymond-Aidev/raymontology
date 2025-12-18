import { Outlet } from 'react-router-dom'
import { Header, Footer } from '../components/common'

function MainLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-dark-bg">
      {/* Header */}
      <Header />

      {/* Main Content */}
      <main className="flex-1 w-full">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <Outlet />
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </div>
  )
}

export default MainLayout
