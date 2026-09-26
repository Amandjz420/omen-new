import {Alert, Box, Button, Center, Paper, PasswordInput, Stack, Text, TextInput, Title} from '@mantine/core';
import {useState} from 'react';
import {useSession} from '../app/session.jsx';
import {Wordmark} from '../app/Wordmark.jsx';
import {LoadingState} from '../components/States.jsx';
import classes from './Gate.module.css';

function Frame({children}) {
  return <Box className={classes.page}>
    <Box className={classes.band}><Wordmark size="lg"/></Box>
    <Center className={classes.body}><Paper withBorder p="xl" w="min(440px, 100%)">{children}</Paper></Center>
  </Box>;
}

/** Signs people in, and holds them at the password or no-access step as the
 * previous interface did, before the workspace opens. */
export function Gate({children}) {
  const {session, loadError} = useSession();
  if (session === undefined) return <LoadingState label="Connecting to the workspace"/>;
  if (session === null) return <SignIn loadError={loadError}/>;
  if (session.passwordRequired) return <SetPassword/>;
  if (!session.staff) return <NoAccess/>;
  return children;
}

function SignIn({loadError}) {
  const {signIn} = useSession();
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    const f = new FormData(event.currentTarget);
    setBusy(true); setError(null);
    try {await signIn(f.get('username'), f.get('password'));} catch (e) {setError(e);} finally {setBusy(false);}
  }
  return <Frame><form onSubmit={submit}><Stack>
    <Title order={1}>Sign in</Title>
    <Text size="sm" c="dimmed">Use the username and password issued to you.</Text>
    {(error || (loadError && loadError.status === 0)) && <Alert color="red" variant="light" role="alert">{(error || loadError).message}</Alert>}
    <TextInput name="username" label="Username" autoComplete="username" required autoFocus/>
    <PasswordInput name="password" label="Password" autoComplete="current-password" required/>
    <Button type="submit" loading={busy}>Sign in</Button>
  </Stack></form></Frame>;
}

function SetPassword() {
  const {session, changePassword, signOut} = useSession();
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    const f = Object.fromEntries(new FormData(event.currentTarget));
    if (f.new_password !== f.confirm_password) {setError(new Error('The new passwords do not match.')); return;}
    setBusy(true); setError(null);
    try {await changePassword(f.current_password, f.new_password);} catch (e) {setError(e);} finally {setBusy(false);}
  }
  return <Frame><form onSubmit={submit}><Stack>
    <Title order={1}>Choose your password</Title>
    <Text size="sm" c="dimmed">You are signed in as {session.username} with a temporary password. Choose your own to continue.</Text>
    {error && <Alert color="red" variant="light" role="alert">{error.message}</Alert>}
    <PasswordInput name="current_password" label="Temporary password" autoComplete="current-password" required/>
    <PasswordInput name="new_password" label="New password" autoComplete="new-password" required
                   description="At least eight characters. Not a common password, your username, or numbers only."/>
    <PasswordInput name="confirm_password" label="Confirm new password" autoComplete="new-password" required/>
    <Button type="submit" loading={busy}>Save password and continue</Button>
    <Button variant="subtle" onClick={signOut} disabled={busy}>Sign out</Button>
  </Stack></form></Frame>;
}

function NoAccess() {
  const {session, signOut} = useSession();
  return <Frame><Stack>
    <Title order={1}>Your account has no workspace access yet</Title>
    <Text size="sm" c="dimmed">You are signed in as {session.username}. Ask your administrator to assign you a role.</Text>
    <Button variant="light" onClick={signOut}>Sign out</Button>
  </Stack></Frame>;
}
