import { Navigate, Route, Routes } from "react-router-dom";
import { GuestRoute, ProtectedRoute } from "./components/RouteGuards";
import { MarketplaceLayout, BrowseItems, ItemDetails, ListingForm } from "./pages/Marketplace";
import MyBookings from "./pages/Bookings";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

export default function App() {
  return (
    <Routes>
      <Route element={<MarketplaceLayout />}>
        <Route path="/" element={<BrowseItems />} />
        <Route path="/my-bookings" element={<ProtectedRoute><MyBookings /></ProtectedRoute>} />
        <Route path="/my-listings" element={<ProtectedRoute><BrowseItems mine /></ProtectedRoute>} />
        <Route path="/items/new" element={<ProtectedRoute><ListingForm key="new" /></ProtectedRoute>} />
        <Route path="/items/:id/edit" element={<ProtectedRoute><ListingForm key="edit" /></ProtectedRoute>} />
        <Route path="/items/:id" element={<ItemDetails />} />
      </Route>
      <Route
        path="/login"
        element={
          <GuestRoute>
            <LoginPage />
          </GuestRoute>
        }
      />
      <Route
        path="/register"
        element={
          <GuestRoute>
            <RegisterPage />
          </GuestRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
