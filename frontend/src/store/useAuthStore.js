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
    set({ user: userData });
  },
  logout: () => {
    localStorage.removeItem('user');
    set({ user: null });
  }
}));
