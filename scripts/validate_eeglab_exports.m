function validate_eeglab_exports(export_dir)
%VALIDATE_EEGLAB_EXPORTS Load every exported .set and check event timing.

if nargin < 1
    export_dir = fullfile(pwd, 'outputs', 'eeglab_sample');
end

files = dir(fullfile(export_dir, '*.set'));
assert(~isempty(files), 'No .set files found in %s', export_dir);

for index = 1:numel(files)
    EEG = pop_loadset('filename', files(index).name, 'filepath', export_dir);
    EEG = eeg_checkset(EEG, 'eventconsistency');
    assert(size(EEG.data, 1) == EEG.nbchan, 'Channel mismatch: %s', files(index).name);
    assert(size(EEG.data, 2) == EEG.pnts, 'Point mismatch: %s', files(index).name);
    assert(EEG.trials == 1, 'Expected continuous data: %s', files(index).name);
    assert(isfield(EEG.chanlocs, 'original_label'), ...
        'Missing original channel labels: %s', files(index).name);
    assert(isfield(EEG.chanlocs, 'raw_index'), ...
        'Missing original channel indices: %s', files(index).name);
    assert(numel(EEG.etc.original_channel_ids) == EEG.nbchan, ...
        'Original channel ID count mismatch: %s', files(index).name);
    assert(numel(EEG.etc.channel_roles) == EEG.nbchan, ...
        'Channel role count mismatch: %s', files(index).name);
    original_labels = string({EEG.chanlocs.original_label});
    channel_types = string({EEG.chanlocs.type});
    dc_mask = ~cellfun('isempty', regexp(cellstr(original_labels), '^POL DC(?:0[1-9]|1[0-6])$', 'once'));
    assert(sum(dc_mask) == 16, 'Expected 16 auxiliary DC inputs: %s', files(index).name);
    assert(all(channel_types(dc_mask) == "MISC"), ...
        'DC inputs must be typed MISC: %s', files(index).name);
    ac_mask = startsWith(original_labels, "POL AC");
    assert(all(channel_types(ac_mask) == "SEEG"), ...
        'AC contacts must remain typed SEEG: %s', files(index).name);

    if ~isempty(EEG.event)
        onset_events = find(strcmp({EEG.event.type}, 'seizure_onset'));
        assert(numel(onset_events) == 1, 'Expected one onset marker: %s', files(index).name);
        event = EEG.event(onset_events);
        recovered_seconds = (event.latency - 1) / EEG.srate;
        assert(abs(recovered_seconds - event.onset_seconds) < 1e-9, ...
            'Onset timing mismatch: %s', files(index).name);
    end
    fprintf('OK  %s  channels=%d points=%d events=%d\n', ...
        files(index).name, EEG.nbchan, EEG.pnts, numel(EEG.event));
end
end
