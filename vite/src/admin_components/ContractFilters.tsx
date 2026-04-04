import { router } from "@inertiajs/react";
import { Button, Fieldset, Group, Input, NativeSelect, NumberInput, Popover, SegmentedControl, Stack, Table, TagsInput, Text, TextInput } from "@mantine/core";
import { IconPencil, IconTrash } from "@tabler/icons-react";
import { useState } from "react";
import { FILTERS, ValueTypes } from "../types";

export interface SavedFilter {
    type: string;
    name: string;
    value: any;
}

export default FilterManagement;
const ERROR_TEXT = "⛔ Error";
const WARNING_TEXT = "⚠️ Warning";
const INFO_TEXT = "Info";

function FilterDisplay({filter}: {filter: SavedFilter})
{
    const [opened, setOpened] = useState(false);

    const filter_key = JSON.stringify(filter);
    return (<Table.Tr>
            <Table.Td width={110}>{filter.type === "Error" ? ERROR_TEXT : WARNING_TEXT}</Table.Td>
            <Table.Td>{FILTERS.find((x) => x.value === filter.name)?.label}</Table.Td>
            <Table.Td>{filter.value?.toLocaleString()}</Table.Td>
            <Table.Td width={30}><Button disabled size="compact-xs" variant="transparent"><IconPencil /></Button></Table.Td>
            <Table.Td width={30}>
                <Popover radius={10} withArrow trapFocus arrowSize={20} opened={opened} onChange={setOpened}>
                    <Popover.Target>
                        <Button size="compact-xs" onClick={() => setOpened(!opened)} variant="transparent"><IconTrash color="darkred" /></Button>
                    </Popover.Target>
                    <Popover.Dropdown>
                        <Text ta="center" pb={5}>Are you sure?</Text>
                        <Group>
                            <Button color="teal" onClick={() => router.delete("/admin/filters", {data: {filter: filter_key}})}>Yes</Button>
                            <Button onClick={() => setOpened(false)}>No</Button>
                        </Group>
                    </Popover.Dropdown>
                </Popover>
            </Table.Td>
        </Table.Tr>);
}

export function FilterManagement({filters}: {filters: SavedFilter[]}) {

    const filter_data = filters.map((filter, i) => {
        return <FilterDisplay key={i} filter={filter} />
    });

    return (
        <Stack p={15}>
            <AddFilterForm />

            <Fieldset legend="Current filters">
                <Table withTableBorder striped>
                    <Table.Thead>
                        <Table.Tr>
                            <Table.Th>Severity</Table.Th>
                            <Table.Th>Filter Type</Table.Th>
                            <Table.Th>Value</Table.Th>
                            <Table.Th />
                            <Table.Th />
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>{filter_data}</Table.Tbody>
                </Table>
            </Fieldset>
        </Stack>
    );
}

function AddFilterForm() {
    const [filter_type, set_filter_type] = useState('Warning');
    const [filter_value, set_filter_value] = useState();
    const [filter_name, set_filter_name] = useState('fuelRounding');

    return (
        <Fieldset legend="Add new filter">
            <Input.Wrapper label="Filter Type">
                <SegmentedControl
                    ml={15}
                    mb={10}
                    withItemsBorders={false}
                    value={filter_type}
                    onChange={set_filter_type}
                    data={[
                        { label: WARNING_TEXT, value: "Warning" },
                        { label: ERROR_TEXT, value: "Error" },
                        { label: INFO_TEXT, value: "Info"}]}
                />
            </Input.Wrapper>
            <Group>
                <NativeSelect
                    value={filter_name}
                    onChange={(event) => set_filter_name(event.currentTarget.value)}
                    data={FILTERS}
                />
                <FilterInputs type={FILTERS.find(x => x.value === filter_name)?.type} value={filter_value} set_value={set_filter_value} />
            </Group>
            <Button mt={10} size="compact-sm" onClick={() => router.post("/admin/filters", { name: filter_name, type: filter_type, value: filter_value })}>Add Filter</Button>
        </Fieldset>
    );
}

function FilterInputs({type, value, set_value} : {type: ValueTypes | undefined, value: any, set_value: (arg0: any) => void}) {
    return ((() => {
        switch (type) {
            case ValueTypes.NUMBER:
                return <NumberInput allowDecimal={false} defaultValue={0} thousandSeparator="," value={value} onChange={set_value} />
            case ValueTypes.STRING:
                return <TextInput value={value} onChange={(event) => set_value(event.currentTarget.value)} />
            case ValueTypes.LIST:
                return <TagsInput value={value} onChange={set_value} />
            case ValueTypes.NONE:
                return <></>
            default:
                return <>Unknown value type {type}</>
        }
    })());
}