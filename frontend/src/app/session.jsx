import {createContext, useCallback, useContext, useEffect, useState} from 'react';
import {useQueryClient} from '@tanstack/react-query';
import {api, post, SIGNED_OUT} from '../lib/api.js';

const SessionContext = createContext(null);

/** Who is signed in, and whether they must choose a password or lack access.
 * undefined while loading; null when signed out. */
export function SessionProvider({children}) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState(undefined);
  const [loadError, setLoadError] = useState(null);
  const apply = s => setSession(s?.username
    ? {username: s.username, staff: Boolean(s.staff), passwordRequired: Boolean(s.password_change_required)} : null);

  useEffect(() => {
    api('session/').then(apply).catch(e => {setLoadError(e); setSession(null);});
  }, []);

  // Any request answered "sign in to continue" means the session has ended.
  useEffect(() => {
    const ended = () => {
      queryClient.clear();
      setLoadError(Object.assign(new Error('Your session has ended. Sign in again to continue.'), {status: 401}));
      setSession(null);
    };
    globalThis.addEventListener(SIGNED_OUT, ended);
    return () => globalThis.removeEventListener(SIGNED_OUT, ended);
  }, [queryClient]);

  const signIn = useCallback(async (username, password) => {
    apply(await post('login/', {username, password}));
    setLoadError(null);
  }, []);
  const signOut = useCallback(async () => {
    await post('logout/');
    queryClient.clear();                        // nothing from this session is left for the next person
    apply(await api('session/'));
  }, [queryClient]);
  const changePassword = useCallback(async (current, next) => {
    await post('password/', {current_password: current, new_password: next});
    apply(await api('session/'));
  }, []);

  return <SessionContext.Provider value={{session, loadError, signIn, signOut, changePassword}}>{children}</SessionContext.Provider>;
}

export const useSession = () => useContext(SessionContext);
