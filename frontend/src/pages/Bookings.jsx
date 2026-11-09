import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { api, parseApiErrors } from '../api';
import { useAuth } from '../auth';

function message(error) {
  if (!error.data) return error.message;
  const parsed = parseApiErrors(error.data);
  return [...parsed.form, ...Object.entries(parsed.fields).map(([key, value]) => `${key.replaceAll('_', ' ')}: ${value}`)].join(' ');
}
function today() {
  // Match the API's UTC calendar dates.
  return new Date().toISOString().slice(0, 10);
}

export function BookingForm({ item }) {
  const { user, token, loading } = useAuth();
  const navigate = useNavigate();
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [availability, setAvailability] = useState(null);
  const [availabilityRevision, setAvailabilityRevision] = useState(0);
  const [availabilityError, setAvailabilityError] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true; setAvailability(null); setAvailabilityError('');
    api(`/api/items/${item.id}/availability/`).then(data => { if (active) setAvailability(data); }).catch(err => { if (active) setAvailabilityError(message(err)); });
    return () => { active = false; };
  }, [item.id, availabilityRevision]);
  const days = start && end ? Math.round((Date.parse(end) - Date.parse(start)) / 86400000) + 1 : 0;
  const overlap = availability?.booked_periods.some(period => start && end && start <= period.end_date && end >= period.start_date);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      await api('/api/bookings/', { method: 'POST', token, body: { item: item.id, start_date: start, end_date: end } });
      navigate('/my-bookings', { state: { message: 'Booking confirmed. A simulated payment hold is active; no money was charged.' } });
    } catch (err) { setError(message(err)); } finally { setBusy(false); }
  }
  if (loading) return <p role="status">Checking your session…</p>;
  if (user?.id === item.owner) return null;
  if (!item.availability) return <p>This item is currently unavailable for booking.</p>;
  return <section className="booking-panel"><h2>Plan your rental</h2><p className="optional">Dates include both the first and last day. Calendar dates use UTC.</p>
    {availabilityError && <p className="alert" role="alert">{availabilityError}</p>}
    {!availability && !availabilityError && <p role="status">Checking booked dates…</p>}
    {availability?.booked_periods.length > 0 && <details><summary>View booked dates</summary><ul>{availability.booked_periods.map((period, index) => <li key={index}>{period.start_date} – {period.end_date}</li>)}</ul></details>}
    <button type="button" className="secondary" disabled={busy} onClick={() => setAvailabilityRevision(value => value + 1)}>Refresh booked dates</button>
    {!user ? <p><Link to="/login" state={{ from: `/items/${item.id}` }}>Log in to book this item</Link></p> : <form onSubmit={submit}>
      <label>Start date<input required type="date" min={today()} value={start} onChange={e => { setStart(e.target.value); setError(''); }} /></label>
      <label>End date<input required type="date" min={start || today()} value={end} onChange={e => { setEnd(e.target.value); setError(''); }} /></label>
      {days > 0 && <p><strong>{(Number(item.price_per_day) * days).toFixed(2)}</strong> total · {days} {days === 1 ? 'day' : 'days'}</p>}
      {overlap && <p className="alert" role="alert">These dates overlap an existing booking. Choose other dates.</p>}
      {error && <p className="alert" role="alert">{error}</p>}
      <p className="optional">Mock payment only. Booking creates a simulated hold. No card information or real charge.</p>
      <button disabled={busy || overlap || days < 1 || start < today()}>{busy ? 'Booking…' : 'Book with mock hold'}</button>
    </form>}
  </section>;
}

export default function MyBookings() {
  const { token, user } = useAuth();
  const [params, setParams] = useSearchParams();
  const page = params.get('page') || '1';
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const location = useLocation();
  const [success, setSuccess] = useState(location.state?.message || '');
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true; setLoading(true); setError('');
    api(`/api/bookings/?page=${encodeURIComponent(page)}`, { token }).then(result => { if (active) setData(result); }).catch(err => { if (active) setError(message(err)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token, page, revision]);
  async function transition(booking, operation) {
    if (operation === 'open-dispute' && !window.confirm('Flag an open dispute? The mock hold will remain active until the dispute is resolved by support.')) return;
    setBusy(true); setError(''); setSuccess('');
    try {
      const updated = await api(`/api/bookings/${booking.id}/${operation}/`, { method: 'POST', token });
      setData(current => ({ ...current, results: current.results.map(row => row.id === booking.id ? updated : row) }));
      setSuccess(operation === 'cancel' ? 'Booking cancelled. The simulated hold is cancelled.' : operation === 'complete' ? 'Rental completed. The simulated hold is released.' : 'Dispute flagged. The simulated hold remains active.');
    } catch (err) { setError(message(err)); } finally { setBusy(false); }
  }
  return <><section className="market-hero"><p className="eyebrow">Your rentals, in one place</p><h1>My Bookings</h1><p>Track your rentals and bookings for items you own.</p></section>
    {success && <p className="success" role="status">{success}</p>}
    {error && <p className="alert" role="alert">{error} <button className="secondary" onClick={() => setRevision(r => r + 1)}>Refresh</button></p>}
    {loading ? <p role="status">Loading bookings…</p> : data && <>{!data.results.length ? <div className="empty-state"><h2>No bookings yet</h2><Link to="/">Find something to rent</Link></div> : <div className="booking-list">{data.results.map(booking => {
      const active = ['pending', 'confirmed'].includes(booking.status);
      const owner = booking.owner === user.id;
      return <article key={booking.id} className="booking-card"><div className="results-heading"><h2><Link to={`/items/${booking.item}`}>{booking.item_title}</Link></h2><span className="availability">{booking.status}</span></div><p>Booking #{booking.id} · {owner ? `Rented by ${booking.renter_name}` : `Listed by ${booking.owner_name}`}</p><dl><div><dt>Rental dates (inclusive)</dt><dd>{booking.start_date} – {booking.end_date}</dd></div><div><dt>Total rental price</dt><dd>{booking.total_price}</dd></div><div><dt>Mock payment status</dt><dd>{booking.payment?.state ? booking.payment.state[0].toUpperCase() + booking.payment.state.slice(1) : 'Unavailable'} · {booking.payment?.amount}</dd></div></dl><p className="optional">Simulation only · No money charged</p>{booking.dispute_open && <p className="alert">Open dispute — the hold stays active pending resolution.</p>}
      {active && !booking.dispute_open && <div className="actions">{today() < booking.start_date && <button className="secondary" disabled={busy} onClick={() => transition(booking, 'cancel')}>Cancel booking</button>}{owner && today() > booking.end_date && <button disabled={busy} onClick={() => transition(booking, 'complete')}>Confirm successful completion</button>}{today() >= booking.start_date && <button className="secondary" disabled={busy} onClick={() => transition(booking, 'open-dispute')}>Flag open dispute</button>}</div>}</article>;
    })}</div>}<div className="pagination"><button disabled={!data.previous || busy} onClick={() => setParams({ page: String(Number(page) - 1) })}>Previous</button><span>Page {page}</span><button disabled={!data.next || busy} onClick={() => setParams({ page: String(Number(page) + 1) })}>Next</button></div></>}
  </>;
}
