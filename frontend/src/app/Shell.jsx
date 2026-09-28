import {AppShell, Group, Menu, NavLink, ScrollArea, Stack, Text, UnstyledButton} from '@mantine/core';
import {useDisclosure, useMediaQuery} from '@mantine/hooks';
import {notifications} from '@mantine/notifications';
import {useEffect} from 'react';
import {Link, NavLink as RouterLink, Outlet, useLocation} from 'react-router';
import {PHONE_TABS, WORKSPACES} from './nav.js';
import {useSession} from './session.jsx';
import {Wordmark} from './Wordmark.jsx';
import classes from './Shell.module.css';

export function Shell() {
  const {session, signOut} = useSession();
  const [opened, {toggle, close}] = useDisclosure(false);
  const phone = useMediaQuery('(max-width: 47.99em)');
  const location = useLocation();
  useEffect(close, [location.pathname]);          // choosing a page closes the phone menu

  async function leave() {
    try {await signOut();} catch (e) {notifications.show({color: 'red', title: 'Sign-out failed', message: e.message});}
  }

  return <AppShell header={{height: 64}} navbar={{width: 248, breakpoint: 'sm', collapsed: {mobile: !opened}}}
                   footer={{height: 'calc(60px + env(safe-area-inset-bottom, 0px))', collapsed: !phone}} padding={{base: 'sm', sm: 'xl'}}>
    <AppShell.Header className={classes.header}>
      <Group h="100%" px="md" justify="space-between" wrap="nowrap">
        {/* On a phone the bottom bar's Menu opens navigation; a header hamburger would duplicate it. */}
        <UnstyledButton component={Link} to="/" aria-label="Omen Assessors, my work"><Wordmark/></UnstyledButton>
        <Menu position="bottom-end" withinPortal>
          <Menu.Target><UnstyledButton className={classes.user} aria-label={`Account: ${session.username}`}>{session.username}</UnstyledButton></Menu.Target>
          <Menu.Dropdown>
            <Menu.Label>Signed in as {session.username}</Menu.Label>
            <Menu.Item onClick={leave}>Sign out</Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </Group>
    </AppShell.Header>

    {/* Closed on a phone, the menu is slid off-screen; inert takes it out of the tab order
        and the accessibility tree too, so its links are not reached or read unseen. */}
    <AppShell.Navbar p="sm" aria-label="Main" inert={phone && !opened ? true : undefined}>
      <ScrollArea type="auto">
        <Stack gap="md" py="xs">
          {WORKSPACES.map(group => <div key={group.label}>
            {group.items.length > 1 && <Text size="xs" fw={600} c="dimmed" px="sm" mb={4}>{group.label}</Text>}
            {group.items.map(item => <NavLink key={item.to} component={RouterLink} to={item.to} end={item.end}
              label={item.label} className={classes.navlink}/>)}
          </div>)}
        </Stack>
      </ScrollArea>
    </AppShell.Navbar>

    <AppShell.Main className={classes.main}><Outlet/></AppShell.Main>

    <AppShell.Footer className={classes.tabbar} aria-label="Quick navigation">
      {PHONE_TABS.map(tab => <UnstyledButton key={tab.to} component={RouterLink} to={tab.to} end={tab.end} className={classes.tab}>{tab.label}</UnstyledButton>)}
      <UnstyledButton className={classes.tab} onClick={toggle} aria-expanded={opened}>Menu</UnstyledButton>
    </AppShell.Footer>
  </AppShell>;
}
