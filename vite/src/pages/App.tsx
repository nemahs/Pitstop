import { Link } from '@inertiajs/react';
import * as mantine from '@mantine/core';
import { IconAssemblyFilled, IconChevronRight, IconContract, IconGasStation, IconLogout } from '@tabler/icons-react';
import { useState } from 'react';

interface User {
  name: string;
  is_authenticated: boolean;
  permissions: Permissions;


}

enum Permissions {
  ADMIN = 1 << 0
}

function has_permission(user: User, permission: Permissions): boolean {
  return (user.permissions & permission) === permission;
}

function Header({raw_user, auth_url}: {raw_user: string, auth_url: string}) {
  let user: User = JSON.parse(raw_user);

  let rightSide = user.is_authenticated ? (
    <mantine.Group justify='flex-end'>
      <mantine.Title order={5}>Logged in as: {has_permission(user, Permissions.ADMIN) && "Admin"} {user.name}</mantine.Title>
      <mantine.Button component='a' href="/logout" variant='default' rightSection={<IconLogout />}>Logout</mantine.Button>
    </mantine.Group>
  ) : (
    <mantine.Group justify="flex-end">
      <a href={auth_url}>Test GICE Login</a>
     {/*<LoginAnchor client_id={client_id} scopes={scopes} redirect_uri={redirect_uri}><img height={35} src="/static/eve-sso-login-black-large.png"></img></LoginAnchor> */}
    </mantine.Group>
  );


  return (
    <mantine.Group grow preventGrowOverflow={false}>
      <mantine.Image src="/static/bee_pitstop.png" radius='sm' w='auto' fit='contain' h={35} pl={10} />
      <mantine.Title order={3}>Pitstop</mantine.Title>
      {rightSide}
    </mantine.Group>
  );
}


interface Notification {
  severity: string;
  message: string;
}

function Notifications({messages}: {messages: string})
{
  let parsed_messages: Array<Notification> = JSON.parse(messages)

  const [filtered_mesages, setMessages] = useState(parsed_messages)

  const message_elements = filtered_mesages.map(({severity, message}) => {
    let color: string = "blue"
    switch (severity) {
      case "error":
        color = "red";
        break;
      case "warning":
        color = "yellow";
        break;
      case "message":
        color = "cyan";
        break;
    }

    return (<mantine.Notification key={message} withCloseButton withBorder color={color} 
      onClose={() => setMessages(filtered_mesages.filter(a => a.message !== message))}>
      {message}
      </mantine.Notification>);
  });

  return (
    <mantine.Stack>
      {message_elements}
    </mantine.Stack>

  );
}

export function Layout({current_user, name, messages, is_admin, auth_url, children} : {current_user: string, name: string, messages: string, is_admin: boolean, auth_url: string, children: any}) {
  return (
    <mantine.MantineProvider defaultColorScheme='dark'>
      <mantine.AppShell header={{height: 40}} navbar={{width: 200, breakpoint: 'md'}}>

        <mantine.AppShell.Header>
          <Header raw_user={current_user} auth_url={auth_url} />
        </mantine.AppShell.Header>

        <mantine.AppShellNavbar>
          <mantine.NavLink active={name === "Contracts" ? true : false} component={Link} href="/contracts" label="All Contracts" rightSection={<IconChevronRight />} leftSection={<IconContract />} />
          <mantine.NavLink active={name === "Fuelling" ? true : false} component={Link} prefetch href="/fuelling" label="Fueling" rightSection={<IconChevronRight />} leftSection={<IconGasStation />} />
          <mantine.NavLink disabled={!is_admin} active={name === "Admin" ? true : false} component={Link} href="/admin" label="Admin" rightSection={<IconChevronRight />} leftSection={<IconAssemblyFilled />} />

        </mantine.AppShellNavbar>

        <mantine.AppShell.Main>
          {messages && <Notifications messages={messages} />}
          {children}
        </mantine.AppShell.Main>
      </mantine.AppShell>
    </mantine.MantineProvider>
  )
}

function App(props: any) {
  return (
    <Layout {...props}>
      {props.children}
    </Layout>
  )
}

export default App
