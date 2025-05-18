import { router } from "@inertiajs/core";
import { Button, Fieldset, Flex, Group, NumberInput, Popover, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconTrash } from "@tabler/icons-react";
import { useState } from "react";
import useSWR from "swr";
import { NamedItem } from "../types";

const fetcher = (url: string | URL) => fetch(url).then((res) => res.json());

export function StationManagement() {
    return (
        <Stack p={15}>
            <Fieldset legend="Current Fuelling Stations">
                <StationList />
            </Fieldset>
            <Fieldset legend="Add New Station">
                <AddStation />
            </Fieldset>
        </Stack>
    )
}

function StationList() {
    const { data, isLoading }: {data: NamedItem[], isLoading: boolean} = useSWR("/fuel/stations/", fetcher, {refreshInterval: 5000});

    let station_elements: JSX.Element | JSX.Element[] = <></>;

    if (!isLoading && data !== undefined) 
    {
        station_elements = data.map((station: NamedItem) => (
            <Station key={station.id} station={station} />
        ));
    }

    return (
        <Skeleton visible={isLoading} height={400}>
            <Table withRowBorders striped withTableBorder>
                <Table.Tbody>
                    {station_elements}
                </Table.Tbody>
            </Table>
        </Skeleton>
    );
}

function AddStation() {
    const [station_id, set_station_id] = useState<string | number>();

    return (
    <Flex align={"flex-end"} gap={"sm"}>
      <NumberInput value={station_id} onChange={set_station_id} allowDecimal={false} label="Station ID" hideControls></NumberInput>  
      <Button onClick={() => router.post(`/fuel/stations/${station_id}`, {}, { only: ['StationList'] })}>Add Station</Button>
    </Flex>
    );
}

function Station({ station }: {station: NamedItem}) {
    const [opened, setOpened] = useState(false);

    return (
    <Table.Tr>
        <Table.Td style={{whiteSpace: "nowrap"}}>
            <Text>{station.name}</Text>
        </Table.Td>
        <Table.Td w="100%" maw={0}>
            <Popover radius={10} arrowSize={20} withArrow trapFocus opened={opened} onChange={setOpened} >
                <Popover.Target>
                    <Button color="red" size="sm" leftSection={<IconTrash />} onClick={() => setOpened(!opened)}>Remove</Button>
                </Popover.Target>
                <Popover.Dropdown>
                    <Text ta="center" pb={5}>Are you sure?</Text>
                    <Group>
                        <Button color="teal" onClick={() => router.delete(`/fuel/stations/${station.id}`, { only: ['StationList'] })}>Yes</Button>
                        <Button onClick={() => setOpened(false)}>No</Button>
                    </Group>
                </Popover.Dropdown>
            </Popover>
        </Table.Td>
    </Table.Tr>); 
}