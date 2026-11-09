import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, parseApiErrors } from '../api';
import { BookingForm } from './Bookings';
import { useAuth } from '../auth';

export function MarketplaceLayout() {
  const { user, logout, loading } = useAuth();
  return <><header className="market-nav"><Link className="logo" to="/">RentNear<span>Borrow more. Own less.</span></Link><nav aria-label="Main navigation"><NavLink to="/" end>Browse Items</NavLink><NavLink to="/items/new">Create Listing</NavLink><NavLink to="/my-listings">My Listings</NavLink><NavLink to="/my-bookings">My Bookings</NavLink>{!loading && (user ? <button onClick={logout}>Logout</button> : <Link to="/login">Login</Link>)}</nav></header><main className="market-main"><Outlet /></main><footer className="market-footer">RentNear · Good things, closer to home.</footer></>;
}

function ErrorMessage({ error }) {
  return error ? <p className="alert" role="alert">{error}</p> : null;
}
function errorText(error) {
  if (!error.data) return error.message;
  const parsed = parseApiErrors(error.data);
  return [...parsed.form, ...Object.entries(parsed.fields).map(([key, value]) => `${key.replaceAll('_', ' ')}: ${value}`)].join(' ');
}
function ItemCard({ item }) {
  return <Link className="item-card" to={`/items/${item.id}`}><div className="card-photo">{item.images[0] ? <img src={item.images[0].image} alt={item.title} loading="lazy" /> : <span>No photo yet</span>}<span className="category-tag">{item.category}</span></div><div className="card-copy"><h2>{item.title}</h2><p>{item.location}</p><div><strong>{item.price_per_day}</strong> <span>/ day</span>{!item.availability && <span className="unavailable"> · Unavailable</span>}</div></div></Link>;
}

export function BrowseItems({ mine = false }) {
  const { token } = useAuth();
  const [params, setParams] = useSearchParams();
  const query = params.toString();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState({});
  const location = useLocation();
  useEffect(() => { setDraft(Object.fromEntries(new URLSearchParams(query))); }, [query]);
  useEffect(() => { api('/api/items/categories/').then(setCategories).catch(() => {}); }, []);
  useEffect(() => {
    let active = true;
    setLoading(true); setError('');
    api(`/api/items/${mine ? 'mine/' : ''}?${query}`, { token: mine ? token : undefined }).then(result => { if (active) setData(result); }).catch(err => { if (active) setError(errorText(err)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [query, mine, token]);
  const change = e => setDraft({ ...draft, [e.target.name]: e.target.value });
  function page(delta) { const next = new URLSearchParams(params); next.set('page', Number(params.get('page') || 1) + delta); setParams(next); }
  return <><section className="market-hero"><p className="eyebrow">{mine ? 'Your little rental business' : 'Less buying. More living.'}</p><h1>{mine ? 'My Listings' : 'Find what you need.\nRight around you.'}</h1><p>{mine ? 'Manage your items, photos and availability in one place.' : 'From weekend adventures to everyday projects, rent from your community.'}</p>{mine && <Link className="button-link" to="/items/new">+ Create Listing</Link>}</section>
    {location.state?.message && <p className="success" role="status">{location.state.message}</p>}
    {!mine && <form className="filters" onSubmit={e => { e.preventDefault(); setParams(Object.fromEntries(Object.entries(draft).filter(([key, value]) => key !== 'page' && value))); }}><label className="search-field">What are you looking for?<input name="search" placeholder="Try camera, drill, camping…" value={draft.search || ''} onChange={change} /></label><label>Category<select name="category" value={draft.category || ''} onChange={change}><option value="">All categories</option>{[...new Set([...categories, draft.category].filter(Boolean))].map(c => <option key={c}>{c}</option>)}</select></label><label>Location<input name="location" placeholder="City or neighborhood" value={draft.location || ''} onChange={change} /></label><label>Min price / day<input name="min_price" type="number" min="0" step="0.01" value={draft.min_price || ''} onChange={change} /></label><label>Max price / day<input name="max_price" type="number" min="0" step="0.01" value={draft.max_price || ''} onChange={change} /></label><button>Find items</button><button className="secondary" type="button" onClick={() => { setDraft({}); setParams({}); }}>Clear</button></form>}
    <ErrorMessage error={error} />{loading ? <p role="status">Loading listings…</p> : !error && <><div className="results-heading"><h2>{mine ? 'Your items' : 'Explore nearby'}</h2><span>{data?.count || 0} items</span></div>{data?.results.length ? <div className="item-grid">{data.results.map(item => <ItemCard key={item.id} item={item} />)}</div> : <div className="empty-state"><h2>No items found</h2><p>{mine ? 'Share something useful with your neighbors.' : 'Try a different search or clear your filters.'}</p></div>}<div className="pagination"><button disabled={!data?.previous} onClick={() => page(-1)}>Previous</button><span>Page {params.get('page') || 1}</span><button disabled={!data?.next} onClick={() => page(1)}>Next</button></div></>}
  </>;
}

export function ItemDetails() {
  const { id } = useParams();
  const { user, token } = useAuth();
  const [item, setItem] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  useEffect(() => { let active = true; setItem(null); setError(''); api(`/api/items/${id}/`).then(data => { if (active) setItem(data); }).catch(err => { if (active) setError(errorText(err)); }); return () => { active = false; }; }, [id]);
  async function remove() {
    if (!window.confirm('Delete this listing and its photos?')) return;
    setBusy(true);
    try { await api(`/api/items/${id}/`, { method: 'DELETE', token }); navigate('/my-listings', { state: { message: 'Listing deleted.' } }); } catch (err) { setError(errorText(err)); setBusy(false); }
  }
  return <><Link to="/">← Browse Items</Link>{location.state?.message && <p className="success" role="status">{location.state.message}</p>}<ErrorMessage error={error} />{!item && !error && <p role="status">Loading item…</p>}{item && <div className="detail-layout"><div className="photo-gallery">{item.images.length ? item.images.map(photo => <img key={photo.id} src={photo.image} alt={item.title} />) : <div className="empty-state">No photos yet</div>}</div><article className="detail-copy"><p className="eyebrow">{item.category}</p><h1>{item.title}</h1><p className="detail-price">{item.price_per_day} <small>/ day</small></p><p>{item.location}</p><span className="availability">{item.availability ? 'Available to rent' : 'Currently unavailable'}</span><h2>About this item</h2><p className="description">{item.description}</p><p>Listed by {item.owner_name}</p><BookingForm key={item.id} item={item} />{user?.id === item.owner && <div className="actions"><Link className="button-link" to={`/items/${id}/edit`}>Edit Listing</Link><button className="danger" disabled={busy} onClick={remove}>{busy ? 'Deleting…' : 'Delete Listing'}</button></div>}</article></div>}</>;
}

const initialValues = { title: '', description: '', category: '', price_per_day: '', location: '', availability: true };
export function ListingForm() {
  const { id } = useParams();
  const { token, user } = useAuth();
  const navigate = useNavigate();
  const [values, setValues] = useState(initialValues);
  const [existing, setExisting] = useState([]);
  const [removed, setRemoved] = useState([]);
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(Boolean(id));
  const [loadError, setLoadError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!id) { setValues(initialValues); setExisting([]); setRemoved([]); setFiles([]); setError(''); setLoading(false); return; }
    let active = true; setLoading(true); setLoadError('');
    api(`/api/items/${id}/`, { token }).then(item => { if (!active) return; if (item.owner !== user.id) throw new Error('Only the owner can edit this listing.'); setValues(item); setExisting(item.images); }).catch(err => { if (active) setLoadError(errorText(err)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id, token, user.id]);
  useEffect(() => { const urls = files.map(file => URL.createObjectURL(file)); setPreviews(urls); return () => urls.forEach(url => URL.revokeObjectURL(url)); }, [files]);
  function chooseFiles(e) {
    const selected = Array.from(e.target.files);
    if (selected.some(f => !['image/jpeg', 'image/png', 'image/webp'].includes(f.type) || f.size > 5 * 1024 * 1024)) { setError('Use JPEG, PNG or WebP photos, up to 5 MB each.'); e.target.value = ''; return; }
    if (selected.length + existing.length - removed.length > 8) { setError('Choose up to 8 photos in total.'); e.target.value = ''; return; }
    setFiles(selected); setError('');
  }
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    const body = new FormData();
    Object.keys(initialValues).forEach(key => body.append(key, values[key]));
    files.forEach(file => body.append('photos', file));
    removed.forEach(photoId => body.append('remove_image_ids', photoId));
    try { const item = await api(id ? `/api/items/${id}/` : '/api/items/', { method: id ? 'PATCH' : 'POST', body, token }); navigate(`/items/${item.id}`, { state: { message: id ? 'Listing updated.' : 'Your listing is live!' } }); } catch (err) { setError(errorText(err)); } finally { setBusy(false); }
  }
  if (loading) return <p role="status">Loading listing…</p>;
  if (loadError) return <ErrorMessage error={loadError} />;
  return <section className="listing-editor"><p className="eyebrow">Share more, waste less</p><h1>{id ? 'Edit Listing' : 'Create Listing'}</h1><p className="lede">Give your unused things a new adventure.</p><ErrorMessage error={error} /><form onSubmit={submit}>
    {['title', 'description', 'category', 'price_per_day', 'location'].map(key => <label key={key}>{({ title: 'Title', description: 'Description', category: 'Category', price_per_day: 'Rental price / day', location: 'Location' })[key]}{key === 'description' ? <textarea required rows="5" maxLength="10000" value={values[key]} onChange={e => setValues({ ...values, [key]: e.target.value })} /> : <input required type={key === 'price_per_day' ? 'number' : 'text'} min="0" step="0.01" maxLength={key === 'category' ? 100 : 200} list={key === 'category' ? 'categories' : undefined} value={values[key]} onChange={e => setValues({ ...values, [key]: e.target.value })} />}</label>)}
    <datalist id="categories">{['Tools', 'Electronics', 'Outdoor', 'Sports', 'Home', 'Events', 'Other'].map(c => <option key={c} value={c} />)}</datalist>
    <label className="checkbox"><input type="checkbox" checked={values.availability} onChange={e => setValues({ ...values, availability: e.target.checked })} />Available to rent</label>
    <label>Photos <span className="optional">Up to 8 · JPEG, PNG, WebP · 5 MB each</span><input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={chooseFiles} /></label>
    <div className="photo-previews">{existing.filter(photo => !removed.includes(photo.id)).map(photo => <div key={photo.id}><img src={photo.image} alt="Existing listing photo" /><button type="button" onClick={() => setRemoved([...removed, photo.id])}>Remove photo</button></div>)}{previews.map((url, index) => <div key={url}><img src={url} alt={`New photo ${index + 1}`} /><button type="button" onClick={() => setFiles(files.filter((_, i) => i !== index))}>Remove photo</button></div>)}</div>
    <div className="actions"><button disabled={busy}>{busy ? 'Saving…' : id ? 'Save changes' : 'Publish listing'}</button><Link to={id ? `/items/${id}` : '/my-listings'}>Cancel</Link></div>
  </form></section>;
}
