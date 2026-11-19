import { create } from 'zustand';

const getSafeUser = () => {
  try {
    const item = localStorage.getItem('user');
    return item && item !== 'undefined' ? JSON.parse(item) : null;
  } catch (e) {
    localStorage.removeItem('user');
    return null;
  }
};

export const useAuthStore = create((set) => ({
  user: getSafeUser(),
  token: localStorage.getItem('token') || null,
  login: (userData, token) => {
    localStorage.setItem('user', JSON.stringify(userData));
    localStorage.setItem('token', token);
    set({ user: userData, token });
  },
  logout: () => {
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    set({ user: null, token: null });
  }
}));

if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key === 'token' || event.key === 'user' || event.key === null) {
      useAuthStore.setState({
        user: getSafeUser(),
        token: localStorage.getItem('token') || null,
      });
    }
  });
}
