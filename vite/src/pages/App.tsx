import { useState } from 'react'
import * as mantine from '@mantine/core'
import { Link } from '@inertiajs/react';
import { IconLogout, IconChevronRight, IconContract, IconGasStation, IconAssemblyFilled } from '@tabler/icons-react'

interface User {
  name: string;
  is_authenticated: boolean;
}


function Header({raw_user, scopes, client_id}: {raw_user: string, scopes: string, client_id: number}) {
  let user: User = JSON.parse(raw_user);


  let rightSide = user.is_authenticated ? (
    <mantine.Group justify='flex-end'>
      <mantine.Title order={5}>Logged in as: {user.name}</mantine.Title>
      <mantine.Button component='a' href="/logout" variant='default' rightSection={<IconLogout />}>Logout</mantine.Button>
    </mantine.Group>
  ) : (
    <mantine.Group justify="flex-end">
      <LoginAnchor client_id={client_id} scopes={scopes}><img height={35} src="/static/eve-sso-login-black-large.png"></img></LoginAnchor>
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


function LoginAnchor({client_id, scopes, children}: {client_id: number, scopes: string, children: any}) {
 
  let sso_url = "https://login.eveonline.com/v2/oauth/authorize?response_type=code";
  sso_url += `&redirect_uri=${encodeURIComponent('https://pitstop.nemahs.org/login')}`;
  sso_url += `&client_id=${client_id}`;
  sso_url += `&scope=${encodeURIComponent(scopes)}&state=banana`;

  return (
    <a href={sso_url}>{ children }</a>
  )
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

export function Layout({current_user, client_id, scopes, type, messages, children} : {current_user: string, client_id: number, scopes: string, type: any, messages: string, children: any}) {
  return (
    <mantine.MantineProvider defaultColorScheme='dark'>
      <mantine.AppShell header={{height: 40}} navbar={{width: 200, breakpoint: 'md'}}>

        <mantine.AppShell.Header>
          <Header raw_user={current_user} client_id={client_id} scopes={scopes} />
        </mantine.AppShell.Header>

        <mantine.AppShellNavbar>
          <mantine.NavLink active={type.name === "Contracts" ? true : false} component={Link} href="/contracts" label="All Contracts" rightSection={<IconChevronRight />} leftSection={<IconContract />} />
          <mantine.NavLink active={type.name === "Fuelling" ? true : false} component={Link} href="/fuelling" label="Fueling" rightSection={<IconChevronRight />} leftSection={<IconGasStation />} />
          <mantine.NavLink disabled active={type.name === "Admin" ? true : false} component={Link} href="/admin" label="Admin" rightSection={<IconChevronRight />} leftSection={<IconAssemblyFilled />} />

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
