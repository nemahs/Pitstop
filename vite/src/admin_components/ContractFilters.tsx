import { router } from "@inertiajs/react";
import { Button, Fieldset, Group, Input, NativeSelect, NumberInput, SegmentedControl, Stack, Table, TagsInput, TextInput } from "@mantine/core";
import { IconPencil, IconTrash } from "@tabler/icons-react";
import { useState } from "react";
import { FILTERS, ValueTypes } from "../types";

export interface SavedFilter {
    type: string;
    name: string;
    value: any;
}

export default FilterManagement;

function FilterDisplay({filter}: {filter: SavedFilter})
{
    const filter_key = JSON.stringify(filter);
    return (<Table.Tr>
            <Table.Td width={110}>{filter.type === "Error" ? "⛔ Error" : "⚠️ Warning"}</Table.Td>
            <Table.Td>{FILTERS.find((x) => x.value === filter.name)?.label}</Table.Td>
            <Table.Td>{filter.value?.toLocaleString()}</Table.Td>
            <Table.Td width={30}><Button disabled size="compact-xs" variant="transparent"><IconPencil /></Button></Table.Td>
            <Table.Td width={30}><Button size="compact-xs" onClick={() => router.delete("/admin/filters", {data: {filter: filter_key}, preserveUrl: true} )}  variant="transparent"><IconTrash color="darkred" /></Button></Table.Td>
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
                <Table withTableBorder>
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
                    withItemsBorders={false}
                    value={filter_type}
                    onChange={set_filter_type}
                    data={[
                        { label: "⚠️ Warning", value: "Warning" },
                        { label: "⛔ Error", value: "Error" }]}
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