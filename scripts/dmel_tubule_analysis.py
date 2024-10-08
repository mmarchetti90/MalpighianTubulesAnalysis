#!/usr/bin/env python3

### ---------------------------------------- ###

def display_help():

    """
    This function displays a description of the script
    """
    
    help_text = """
    This script processes a cross-sectional video of a D. melanogaster Malpighian
    tubule and outputs the tubule, lumen, and cell width over time.

    Parameters
    ----------
    --help : optional
        Prints this help text and quits.
    --sample_name : string, required
        Name of sample, to be used as prefix for output files.
    --movie : string path, required
        Path to the movie to analyze.
    --make_mask : optional
        If used, this option will convert the movie to a mask.
    --vesicles_removal : optional
        If used, vesicles will be aggressively removed.
        This may cause segmentation errors.
    --remove_background : optional
        If used, this option will remove the background using a no-neighborg
        algorithm prior to masking.
    --scale : float, optional
        Scale used to convert pixels measurements, expressed as unit/pixel.
        Omit or set to 1 if unknown.
    --measurements_spacing : float, optional
        Spacing of measurement along the tubule.
        If a scale is set, the measurement referes to microns, or to pixels, otherwise.
    """

    print(help_text)

### ---------------------------------------- ###

def parse_args():

    """
    This function parses command line arguments
    """
    
    print('Reading command line arguments')
    
    print(f'args = {argv}')

    # Sample name
    sample_name = argv[argv.index('--sample_name') + 1]
    
    # Path to movie (can be relative)
    movie_path = argv[argv.index('--movie') + 1]
    
    # Is the movie already masked?
    if '--make_mask' in argv:
        
        masking = True
        
    else:
        
        masking = False
    
    # Is the movie already masked?
    if '--vesicles_removal' in argv:
        
        vesicles_removal = True
        
    else:
        
        vesicles_removal = False

    # Remove background before masking?
    if '--remove_background' in argv:
        
        remove_background = True
        
    else:
        
        remove_background = False

    if '--scale' in argv:

        scale = float(argv[argv.index('--scale') + 1])

    else:

        scale = 1

    # Spacing in microns of measurements
    if '--measurements_spacing' in argv:
        
        measurements_spacing = float(argv[argv.index('--measurements_spacing') + 1])
        
    else:
        
        measurements_spacing = 20
    
    return sample_name, movie_path, masking, vesicles_removal, remove_background, scale, measurements_spacing

### ---------------------------------------- ###

class malpighian_movie_processing:

    """
    Class for the processing of adult D. melanogaster malpighian tubules cross-
    sectional, maximum-projection movies.

    Parameters
    ----------
    movie_path : string
        Path to movie to be analyzed.
    masking : bool, optional
        Set to true to mask the image, false if the image is already a mask.
        Default = True
    remove_vesicles : bool, optional
        Set to true to aggressively attempt to remove lumen vesicles.
        This may cause segmentation errors.
        Default = False
    cleanup : bool, optional
        Set to True if you want to remove the background using a no-neighborg
        algorithm prior to masking.
        Default = True
    scale : float, optional
        Scale used to convert pixels measurements, expressed as unit/pixel.
        Default = 1
    spacing : float, optional
        Spacing of measurements along the tubule.
        If a scale is set it refers to microns, or to pixels, otherwise.
        Default = 10
    output_prefix : string, optional
        Prefix to be used for output files.
        Default = "data"

    Attributes
    ----------
    movie : np.array
        Movie stored as a numpy array.
        Created on class init.
    results : pd.DataFrame
        Results of the movie analysis.
        Created by process_movie function

    Methods
    -------
    process_movie()
        Processes the movie and creates a results table.
    """

    def __init__(self, movie_path, masking=True, remove_vesicles=False, cleanup=True, scale=1, spacing=10, output_prefix='data'):

        # Set class vars
        self.masking_toggle = masking
        self.remove_vesicles_toggle = remove_vesicles
        self.cleanup_toggle = cleanup
        self.scale = scale
        self.spacing = spacing
        self.output_prefix = output_prefix

        # Import movie
        self.movie = self.image_importer(movie_path)

    ### ------------------------------------ ###
    ### PROCESSING                           ###
    ### ------------------------------------ ###

    def mask_movie(self):

        print('Masking')
    
        masks = []
        for t,(m,threshold) in enumerate(zip(self.movie, self.thresholds)):
        
            # Initial mask
            mask = (m > threshold)
        
            # Clean mask by erosion + expansion (this removes most small objects)
            mask = maxfil(minfil(mask, 3), 3)
        
            # Label foreground objects
            labels, labels_num = label(mask, np.ones((3, 3)))
            labels_areas = [(lb + 1, (labels == lb + 1).sum()) for lb in range(labels_num)]
            labels_areas.sort(key=lambda x: x[1], reverse=True)
        
            # Filter ojects by size
            if labels_num > 5:
        
                index, _ = self.kneedle([la[1] for la in labels_areas])
        
            else:
            
                index = labels_num
            
            good_labels = [la[0] for la in labels_areas[:index] if la[1] > 2500]
        
            # Redefine mask
            mask = np.ones(m.shape)
            mask[np.where(np.isin(labels, good_labels))] = 0
            
            # Fill holes
            for _ in range(3):
                
                mask = maxfil(minfil(mask, 5), 5)
            
            # Structure mask
            mask = self.structure_mask(mask)
            
            masks.append(mask)
            
            print(f'\rMasked {t + 1} / {self.movie.shape[0]} frames', end='')
    
        # Removing vesicles touching the cells
        if self.remove_vesicles_toggle:

            print('\nTrying to remove vescicles touching cells')
            time_deltas = [-10, -5, 5, 10]
            masks_corrected = []
            for t in range(len(masks)):
                
                m_corrected = masks[t].copy()
                
                for td in time_deltas:
                    
                    try:
                    
                        m_corrected_tmp = self.remove_vesicles(masks[t].copy(), masks[t + td])
                
                    except:
                    
                        m_corrected_tmp = np.zeros(masks[t].shape)
                
                    m_corrected[m_corrected_tmp == 3] = 3
                
                masks_corrected.append(m_corrected)

        else:

            masks_corrected = masks
        
        # Make diagnostic mask for m
        diagnostics = []
        for mk,m in zip(masks_corrected, self.movie):
            
            outlines = 255 * ((mk != 0).astype(int) - minfil(mk != 0, 3).astype(int))
            diag = np.stack([outlines, m, np.zeros(m.shape, dtype=int)], axis=-1)
            diagnostics.append(diag)
        
        # Converting to array
        masks_corrected = np.array(masks_corrected)
        diagnostics = np.array(diagnostics)

        # Save mask to file
        self.save_tiff(masks_corrected, f'{self.output_prefix}_mask')
        self.save_tiff(diagnostics, f'{self.output_prefix}_mask-diagnostics')

        self.mask = masks_corrected.copy()

    ### ------------------------------------ ###

    def process_movie(self):

        """
        Main processing function to clean, mask, and analyze the input movie.
        """

        # Masking movie, if required
        if self.masking_toggle:
            
            # Removing background, if required
            if self.cleanup_toggle:
                
                self.movie = self.clean_movie(self.movie, background_multiplier=0.5)
            
                # Save cleaned movie to file
                self.save_tiff(self.movie, f'{self.output_prefix}_clean')
            
            # Thresholding
            self.threshold_movie()

            # Mask image
            self.mask_movie()

        else:

            self.mask = self.movie.copy()

        # Processing
        self.analyze_frames()

        # Plot results
        self.plot_results(normalize=False)
        self.plot_results(normalize=True)

    ### ------------------------------------ ###

    def remove_vesicles(self, m1, m2, min_size=500):
        
        # Find lumen
        lumen_label = 3
        lumen_1, lumen_2 = (m1 == lumen_label), (m2 == lumen_label)
        
        # Find possible vesicles as non-lumen regions that fill up in the m2 time-point
        possible_vesicles = ((lumen_1.astype(int) - lumen_2.astype(int)) == - 1)
        
        # Contract to remove small changes at the edge of the lumen
        possible_vesicles = minfil(possible_vesicles, 5)
        
        # Label foreground objects
        labels, labels_num = label(possible_vesicles, np.ones((3, 3)))
        labels_areas = [(lb + 1, (labels == lb + 1).sum()) for lb in range(labels_num)]
        labels_areas.sort(key=lambda x: x[1], reverse=True)
        
        if not len(labels_areas):
            
            return m1
        
        else:
            
            index, _ = self.kneedle([la[1] for la in labels_areas])
            good_labels = labels_areas[:index]
            good_labels = [la[0] for la in labels_areas[:index] if la[1] >= min_size]
            
            # Remove vesiscles from lumen_1
            if len(good_labels):
                
                lumen_1[np.where(np.isin(labels, good_labels))] = 1
            
            # Filling holes
            lumen_1 = minfil(maxfil(lumen_1, 3), 3)
            lumen_1 = fill(lumen_1)
            
            # Update m1 mask
            m1[np.where(lumen_1)] = lumen_label
            
            return m1

    ### ------------------------------------ ###

    def save_threshold_diagnostics(self, thrs, prefix='threshold'):
    
        # Save to file
        data = pd.DataFrame({'frame' : range(len(thrs)),
                             'threshold' : thrs})
        data.to_csv(f'{prefix}.tsv', sep='\t', index=False, header=True)
        
        # Smooth
        idx, smooth_thrs = self.running_average(thrs, 10)
        
        # Plot data
        plt.figure(figsize=(15, 3))
        plt.plot(thrs, 'g', lw=3)
        plt.plot(idx, smooth_thrs, 'r', lw=3)
        plt.xlabel('Time (frames)')
        plt.tight_layout()
        plt.savefig(f'{prefix}.png', dpi=300)
        plt.close()

    ### ------------------------------------ ###

    def threshold_movie(self):

        """
        Measures intensities along the 4 axis of the image, then pools the measurements, sorts them, and
        uses a Kneedle approach to find an optimal threshold.
        """

        print('Thresholding')
    
        # Find threhsolds via kneedle
        thresholds = []
        for t,m in enumerate(self.movie):
            
            # Get profile along several axes
            ax_1 = m[m.shape[0] // 2,]
            ax_2 = m[:, m.shape[1] // 2]
            ax_3_pnts = self.get_points_in_between(np.array([0, 0]), np.array(m.shape) - 1)
            ax_3 = m[ax_3_pnts[:,0], ax_3_pnts[:,1]]
            ax_4_pnts = self.get_points_in_between(np.array([m.shape[0] - 1, 0]), np.array([0, m.shape[1]]) - 1)
            ax_4 = m[ax_4_pnts[:,0], ax_4_pnts[:,1]]
            
            # Concatenate
            ax = np.concatenate([ax_1, ax_2, ax_3, ax_4])
            
            # Smoothing
            averaging_window = 10
            _, ax = self.running_average(ax, averaging_window)
            
            # Sorting
            ax = np.sort(ax)[::-1]
            
            # Kneedle on ax
            _, threshold = self.kneedle(ax)
            thresholds.append(threshold)
        
        # Running average
        _, thresholds = self.running_average(thresholds, int(len(thresholds) * 0.2), valid_mode=False)

        # Save thresholds to file and plot data
        self.save_threshold_diagnostics(thresholds, f'{self.output_prefix}_thresholds')
        
        self.thresholds = thresholds.copy()
        
    ### ---------------------------------------- ###
    
    @staticmethod
    def clean_movie(mov, background_multiplier=0.5):
        
        """
        Cleans the movie using a no-neigbor deblurring algorithm.
        """

        # Using no-neighbour deblurring (i.e. simulating background by blurring image using different sigmas) to find foreground
        print("Running no-neighbour deblurring")
        
        # Smoothening the image using a mean filter
        clean_mov = correlate(mov, np.ones((1, 3, 3)) / 9, mode="same")
        
        # To make the calculation faster, mov is downscaled to find background
        clean_mov = np.array([np.array(img.fromarray(t).resize((int(t.shape[1] / 4), int(t.shape[0] / 4)))) for t in mov])
        
        # Simulating background
        background = np.zeros(clean_mov.shape)
        
        for sigma in [5, 10, 20]:
            
            background = np.max((background, gaussian(clean_mov, (0, sigma, sigma), mode="reflect")), 0)
        
        clean_mov = (clean_mov - background * background_multiplier) # Adjusting background intensity

        # Reshaping to 8bit
        clean_mov = (clean_mov * 255 / np.max(clean_mov)).astype('int16')
        
        # Restore original size
        clean_mov = np.array([np.array(img.fromarray(m).resize((mov.shape[2], mov.shape[1]))) for m in clean_mov])
        
        clean_mov[clean_mov < 0] = 0

        return clean_mov

    ### ------------------------------------ ###

    @staticmethod
    def structure_mask(unstructured_mask):
        
        """
        Set background areas outside tubule as 1 and 2, and lumen area as 3.
        """

        # Find blank objects (i.e. empty imaging area and tubule lumen)
        labels, labels_num = label(unstructured_mask, np.ones((3, 3)))
        labels_areas = [(lb, (labels == lb + 1).sum()) for lb in range(labels_num)]
        labels_areas.sort(key=lambda x: x[1], reverse=True)
        labels_of_interest = [l[0] + 1 for l in labels_areas[:3]]
        
        # Define lumen as the label with centroid between the centroids of the two background areas
        centroids = [np.median(np.array(np.where(labels == lb)), axis=1) for lb in labels_of_interest]
        ab_distance = np.power(np.sum(np.power(centroids[0] - centroids[1], 2)), 0.5)
        ac_distance = np.power(np.sum(np.power(centroids[0] - centroids[2], 2)), 0.5)
        bc_distance = np.power(np.sum(np.power(centroids[1] - centroids[2], 2)), 0.5)
        
        if ab_distance > ac_distance and ab_distance > bc_distance:
            
            bg1_label, bg2_label, lumen_label = labels_of_interest[0], labels_of_interest[1], labels_of_interest[2]
        
        elif ac_distance > ab_distance and ac_distance > bc_distance:
            
            bg1_label, bg2_label, lumen_label = labels_of_interest[0], labels_of_interest[2], labels_of_interest[1]
        
        elif bc_distance > ab_distance and bc_distance > ac_distance:
            
            bg1_label, bg2_label, lumen_label = labels_of_interest[1], labels_of_interest[2], labels_of_interest[0]
        
        else:
            
            pass # Never going to happen
        
        # Expansion and erosion to close holes and fill small ones
        radius = (10, 10)
        lumen_mask = minfil(maxfil(labels == lumen_label, radius), radius)
        
        # Filling holes
        lumen_mask = fill(lumen_mask)
        
        # Update masked frame
        new_mask = np.zeros(unstructured_mask.shape)
        new_mask[labels == bg1_label] = 1
        new_mask[labels == bg2_label] = 2
        new_mask[lumen_mask] = 3

        return new_mask

    ### ------------------------------------ ###
    ### IMAGE IMPORT/EXPORT                  ###
    ### ------------------------------------ ###

    @staticmethod
    def image_importer(path, max_frames=10000):

        """
        Imports an image as a Numpy array.
        """
        
        print(f'Importing image {path}')
        
        raw = img.open(path)
        
        movie_arr = []
        
        for r in range(0, max_frames):
            
            try:
                
                raw.seek(r)
                movie_arr.append(np.array(raw))
            
            except:
                
                break

        movie_arr = np.array(movie_arr, dtype='int16') # int8 was giving problems, i.e. bright pixels, close to 256, were converted to 0
        
        raw.close()
        
        print("Image has been successfully imported")
        
        return movie_arr

    ### ------------------------------------ ###

    @staticmethod
    def save_tiff(img_arr, output_prefix='pic'):
        
        """
        Exporting mask as multipage tiff
        """
        
        if img_arr[0].shape[-1] == 3: # RGB image
        
            img_arr = [img.fromarray(ia.astype(np.uint8), 'RGB') for ia in img_arr]
        
        else: # Mono-channel image
            
            img_arr = [img.fromarray(ia.astype(np.uint8)) for ia in img_arr]
        
        img_arr[0].save(f'{output_prefix}.tif', "TIFF", save_all=True, append_images=img_arr[1:])

    ### ------------------------------------ ###
    ### TUBULE ANALYSIS                      ###
    ### ------------------------------------ ###

    def analyze_frames(self):

        """
        Wrapper for analyzing each frame.
        """

        # Init results header and list for storage
        results_header = ['frame',
                          'width_measurements',
                          'tubule_mean_width',
                          'tubule_mean_width_std',
                          'lumen_mean_width',
                          'lumen_mean_width_std',
                          'cells_mean_width',
                          'cells_mean_width_std',
                          'lumen_area',
                          'cells_area']
        results = []
        diagnostic_mask = []

        # Measuring tubule, lumen, and cells width, as wells as lumen and cells total area
        for t,m in enumerate(self.mask):
            
            print(f'\rMeasuring frame {t + 1} / {self.mask.shape[0]}', end='')
            new_diagnostics, new_measurements = self.measure_tubule(m)
            diagnostic_mask.append(new_diagnostics)
            m_measurements = [t] + new_measurements
            results.append(m_measurements.copy())

        diagnostic_mask = np.array(diagnostic_mask)
        results = pd.DataFrame(results, columns=results_header)

        # Add normalized and smoothed data for width
        for var in ['tubule', 'lumen', 'cells']:

            # Index at which columns will be inserted
            idx = results.columns.to_list().index(f'{var}_mean_width') + 2

            # Get data
            data = results.loc[:, f'{var}_mean_width'].values.copy()

            # Smooth raw data
            _, smooth_data = self.running_average(data.copy(), 20, valid_mode=False)

            # Normalize in 0-1 range
            norm_factor = data.max()
            norm_data = data / norm_factor

            # Smooth normalized data
            _, smooth_norm_data = self.running_average(norm_data.copy(), 20, valid_mode=False)

            # Store data
            results.insert(idx, f'{var}_smoothed_width', smooth_data)
            results.insert(idx + 1, f'{var}_normalized_width', norm_data)
            results.insert(idx + 2, f'{var}_smoothed_normalized_width', smooth_norm_data)

        # Add normalized and smoothed data for area
        for var in ['lumen', 'cells']:

            # Index at which columns will be inserted
            idx = results.columns.to_list().index(f'{var}_area') + 1

            # Get data
            data = results.loc[:, f'{var}_area'].values.copy()

            # Smooth raw data
            _, smooth_data = self.running_average(data.copy(), 20, valid_mode=False)

            # Normalize in 0-1 range
            norm_factor = data.max()
            norm_data = data / norm_factor

            # Smooth normalized data
            _, smooth_norm_data = self.running_average(norm_data.copy(), 20, valid_mode=False)

            # Store data
            results.insert(idx, f'{var}_smoothed_area', smooth_data)
            results.insert(idx + 1, f'{var}_normalized_area', norm_data)
            results.insert(idx + 2, f'{var}_smoothed_normalized_area', smooth_norm_data)

        # Save to file
        self.save_tiff(diagnostic_mask, f'{self.output_prefix}_measurements-diagnostics')
        results.to_csv(f'{self.output_prefix}_measurements.tsv', sep='\t', index=False, header=True)

        self.results = results.copy()

    ### ------------------------------------ ###

    def measure_tubule(self, m):
        
        # Labels used in structure_mask function
        cells_label, bg1_label, bg2_label, lumen_label = 0, 1, 2, 3
        
        # Init diagnostic mask of measurements
        diagnostic_m = m.copy()
        diagnostic_m[diagnostic_m != 0] = 1
        
        # Measure tubule and lumen area
        cells_area = (m == cells_label).sum() * self.scale**2
        lumen_area = (m == lumen_label).sum() * self.scale**2
        
        # Init lists for tubule, lumen, and cell thickness
        tubule_measurements, lumen_measurements, cells_measurements = [], [], []
        
        # Find the tubule outlines
        tubule_outline_1 = np.stack(np.where((m == bg1_label) != minfil(m == bg1_label, (3, 3)))).T
        tubule_outline_2 = np.stack(np.where((m == bg2_label) != minfil(m == bg2_label, (3, 3)))).T
        
        # Sort outlines coordinates
        tubule_outline_1 = self.sort_coords(tubule_outline_1)
        tubule_outline_2 = self.sort_coords(tubule_outline_2)
        
        # Sorting coordinates based on ax with more variation
        # (e.g. if dy ~ 0 and dx ~ 1, then the tubule is laying on the x axis, etc...)
        # N.B. Using only tubule_outline_1 since the two outlines are ~ parallel
        dy, dx = np.abs((tubule_outline_1[-1,] - tubule_outline_1[0,]) / m.shape)
        if dy > dx:
            
            tubule_outline_1 = tubule_outline_1[np.argsort(tubule_outline_1[:,0]),]
            tubule_outline_2 = tubule_outline_2[np.argsort(tubule_outline_2[:,0]),]
        
        else:
            
            tubule_outline_1 = tubule_outline_1[np.argsort(tubule_outline_1[:,1]),]
            tubule_outline_2 = tubule_outline_2[np.argsort(tubule_outline_2[:,1]),]
        
        # Align the outlines
        if len(tubule_outline_1) > len(tubule_outline_2):
            
            offset = (len(tubule_outline_1) - len(tubule_outline_2)) // 2
            tubule_outline_1 = tubule_outline_1[offset : offset + len(tubule_outline_2)]
        
        elif len(tubule_outline_2) > len(tubule_outline_1):
            
            offset = (len(tubule_outline_2) - len(tubule_outline_1)) // 2
            tubule_outline_2 = tubule_outline_2[offset : offset + len(tubule_outline_1)]
        
        else:
            
            pass
        
        # Every self.spacing microns, calculate lumen and tubule width, as well as cell thickness
        #outline_1_cumsum_length = np.concatenate([[0],
        #                                          np.cumsum(np.sqrt((np.power(tubule_outline_1[1:] - tubule_outline_1[:-1], 2)).sum(axis=1))) * self.scale])
        #outline_2_cumsum_length = np.concatenate([[0],
        #                                          np.cumsum(np.sqrt((np.power(tubule_outline_2[1:] - tubule_outline_2[:-1], 2)).sum(axis=1))) * self.scale])
        outline_1_cumsum_length = np.array([self.scale * i for i in range(len(tubule_outline_1))])
        outline_2_cumsum_length = np.array([self.scale * i for i in range(len(tubule_outline_2))])
        n_measurements = min(int(outline_1_cumsum_length[-1] // self.spacing), int(outline_2_cumsum_length[-1] // self.spacing))
        for i in range(n_measurements + 1):
            
            # Find points on the outlines to use for measurements
            outline_1_pnt = np.where(outline_1_cumsum_length <= (i * self.spacing))[0]
            outline_2_pnt = np.where(outline_2_cumsum_length <= (i * self.spacing))[0]
            
            if not len(outline_1_pnt) or not len(outline_2_pnt):
                
                continue
            
            outline_1_pnt, outline_2_pnt = outline_1_pnt[-1], outline_2_pnt[-1]
            outline_1_pnt, outline_2_pnt = tubule_outline_1[outline_1_pnt], tubule_outline_2[outline_2_pnt]
            
            # Discard if points touche the edges of the image (i.e. profile could be incomplete)
            if outline_1_pnt[0] == 0 or outline_1_pnt[0] == m.shape[0] - 1 or outline_1_pnt[1] == 0 or outline_1_pnt[1] == m.shape[1] -1:
                
                continue
            
            if outline_2_pnt[0] == 0 or outline_2_pnt[0] == m.shape[0] - 1 or outline_2_pnt[1] == 0 or outline_2_pnt[1] == m.shape[1] -1:
                
                continue
            
            # Connect the points and extract the mask profile
            profile_pnts = self.get_points_in_between(outline_1_pnt, outline_2_pnt)
            profile = m[profile_pnts[:, 0], profile_pnts[:, 1]].copy()
            
            # Extract tubule and lumen width, and cells size
            lumen_coords = np.where(profile == lumen_label)[0]
            
            try:
                
                tubule_width = len(profile)
                lumen_width = lumen_coords.max() - lumen_coords.min()
                cells_width = (tubule_width - lumen_width) / 2 # N.B. Divided by two since there's cells on both sides
            
            except:
                
                continue
            
            # Add measurement line to diagnostic_m        
            diagnostic_m[profile_pnts[:,0], profile_pnts[:,1]] = 5
            
            tubule_measurements.append(tubule_width)
            lumen_measurements.append(lumen_width)
            cells_measurements.append(cells_width)
        
        # Add outlines to diagnostic_m
        diagnostic_m[tubule_outline_1[:,0], tubule_outline_1[:,1]] = 3
        diagnostic_m[tubule_outline_2[:,0], tubule_outline_2[:,1]] = 3
        
        # Summarize results
        tubule_mean_width, tubule_mean_width_std = np.mean(tubule_measurements) * self.scale, np.std(tubule_measurements) * self.scale
        lumen_mean_width, lumen_mean_width_std = np.mean(lumen_measurements) * self.scale, np.std(lumen_measurements) * self.scale
        cells_mean_width, cells_mean_width_std = np.mean(cells_measurements) * self.scale, np.std(cells_measurements) * self.scale

        results = [n_measurements,
                   tubule_mean_width, tubule_mean_width_std,
                   lumen_mean_width, lumen_mean_width_std,
                   cells_mean_width, cells_mean_width_std,
                   lumen_area,
                   cells_area]

        return diagnostic_m, results

    ### ------------------------------------ ###
    ### PLOTTING                             ###
    ### ------------------------------------ ###

    def plot_areas(self, normalize=False, plot_name='measurements.png'):
        
        # Plots of unsmoothed data
        fig, axes = plt.subplots(2, 1, sharex=True, sharey=True)
        fig.set_figwidth(15)
        fig.set_figheight(6)

        for ax,var,color in zip(axes.reshape(-1), ['lumen', 'cells'], ['blue', 'green']):
            
            x = self.results.frame.values.copy()
            
            if normalize:
                
                line = self.results.loc[:, f'{var}_normalized_area'].values.copy()

            else:

                line = self.results.loc[:, f'{var}_area'].values.copy()
                
            ax.title.set_text(var)
            ax.plot(x,
                    line,
                    c=color,
                    ls='-',
                    lw=3)
            
            if var == 'lumen':
                
                ax.set_ylabel('Area ($\mu$$m^2$)')

        plt.xlabel('Time (frames)')
        plt.tight_layout()
        plt.savefig(plot_name, dpi=300)
        plt.close()
        
        # Plots of smoothed data
        plt.figure(figsize=(15, 3))
        for var,color in zip(['lumen', 'cells'], ['blue', 'green']):
            
            x = self.results.frame.values.copy()
            
            if normalize:
                
                line = self.results.loc[:, f'{var}_smoothed_normalized_area'].values.copy()

            else:

                line = self.results.loc[:, f'{var}_smoothed_area'].values.copy()

            plt.plot(x,
                     line,
                     c=color,
                     ls='-',
                     lw=3)
        
        plt.ylabel('Area ($\mu$$m^2$)')
        plt.xlabel('Time (frames)')
        plt.tight_layout()
        plt.savefig(plot_name.replace('.png', '_smoothed.png'), dpi=300)
        plt.close()

    ### ------------------------------------ ###

    def plot_results(self, normalize=False):

        """
        Wrapper for plotting functions.
        """

        prefix = f'{self.output_prefix}_measurements_raw' if not normalize else f'{self.output_prefix}_measurements_normalized'
    
        self.plot_widths(normalize, plot_name=f'{prefix}_width.png')
        
        self.plot_areas(normalize, plot_name=f'{prefix}_area.png')

    ### ------------------------------------ ###

    def plot_widths(self, normalize=False, plot_name='measurements.png'):
        
        # Plots of unsmoothed data
        fig, axes = plt.subplots(3, 1, sharex=True, sharey=True)
        fig.set_figwidth(15)
        fig.set_figheight(9)

        for ax,var,color in zip(axes.reshape(-1), ['tubule', 'lumen', 'cells'], ['red', 'blue', 'green']):
            
            x = self.results.frame.values.copy()
            top = self.results.loc[:, f'{var}_mean_width'].values.copy() + self.results.loc[:, f'{var}_mean_width_std'].values.copy()
            middle = self.results.loc[:, f'{var}_mean_width'].values.copy()
            bottom = self.results.loc[:, f'{var}_mean_width'].values.copy() - self.results.loc[:, f'{var}_mean_width_std'].values.copy()
            
            if normalize:
                
                norm_factor = top.max()
                top = top / norm_factor
                middle = middle / norm_factor
                bottom = bottom / norm_factor
                
            ax.title.set_text(var)
            ax.plot(x,
                    middle,
                    c=color,
                    ls='-',
                    lw=3)
            ax.plot(x,
                    top,
                    c=color,
                    ls='--',
                    lw=1)
            ax.plot(x,
                    bottom,
                    c=color,
                    ls='--',
                    lw=1)
            ax.fill_between(x,
                            bottom,
                            top,
                            color=color,
                            alpha=0.25)
            
            if var == 'lumen':
                
                ax.set_ylabel('Width ($\mu$m)')

        plt.xlabel('Time (frames)')
        plt.tight_layout()
        plt.savefig(plot_name, dpi=300)
        plt.close()
        
        # Plots of smoothed data
        plt.figure(figsize=(15, 3))
        for var,color in zip(['tubule', 'lumen', 'cells'], ['red', 'blue', 'green']):
            
            x = self.results.frame.values.copy()
            
            if normalize:

                data = self.results.loc[:, f'{var}_smoothed_normalized_width'].values.copy()

            else:

                data = self.results.loc[:, f'{var}_smoothed_width'].values.copy()
            
            plt.plot(x,
                     data,
                     c=color,
                     ls='-',
                     lw=3)
        
        plt.ylabel('Width ($\mu$m)')
        plt.xlabel('Time (frames)')
        plt.tight_layout()
        plt.savefig(plot_name.replace('.png', '_smoothed.png'), dpi=300)
        plt.close()

    ############################################
    ### UTILITIES                            ###
    ############################################

    @staticmethod
    def get_points_in_between(start, stop):

        """
        Given two points, it finds the necessary ones to connect them.
        """
        
        distance = round(((stop[0] - start[0])**2 + (stop[1] - start[1])**2)**0.5)
        x_shift, y_shift = stop - start
        
        points = []
        
        for d in range(distance):
            
            new_point = [start[0] + round(d * x_shift / distance), start[1] + round(d * y_shift / distance)]
            points.append(new_point)
        
        if list(stop) not in points:
            
            points.append(stop)
        
        points = np.array(points)
        
        return points

    ### ------------------------------------ ### 

    @staticmethod
    def kneedle(vector):
        
        """
        Kneedle to find threshold cutoff.
        """
        
        # Find gradient and intercept
        x0, x1 = 0, len(vector)
        y0, y1 = max(vector), min(vector)
        gradient = (y1 - y0) / (x1 - x0)
        intercept = y0
        
        # Compute difference vector
        difference_vector = [(gradient * x + intercept) - y for x,y in enumerate(vector)]
        
        # Find max of difference_vector and define cutoff
        cutoff_index = difference_vector.index(max(difference_vector))
        cutoff_value = vector[cutoff_index]
        
        return cutoff_index, cutoff_value

    ### ------------------------------------ ###
    
    @staticmethod
    def running_average(vector, window=10, valid_mode=False):
    
        """
        Computes the running average of a list of values or numpy array given a window.
        """
        
        half_window = window // 2
        indexes = np.arange(half_window, len(vector) - half_window, 1)
        smooth = np.array([np.mean(vector[i - half_window : i + half_window]) for i in indexes])
        
        if not valid_mode:
            
            tail_left_indexes = np.arange(0, indexes[0], 1)
            tail_left_smooth = np.array([np.mean(vector[max(0, i - half_window) : i + half_window]) for i in tail_left_indexes])
            tail_right_indexes = np.arange(indexes[-1] + 1, len(vector), 1)
            tail_right_smooth = np.array([np.mean(vector[i - half_window : min(len(vector), i + half_window)]) for i in tail_right_indexes])
            
            indexes = np.concatenate([tail_left_indexes, indexes, tail_right_indexes])
            smooth = np.concatenate([tail_left_smooth, smooth, tail_right_smooth])
        
        return indexes, smooth

    ### ---------------------------------------- ###

    @staticmethod
    def sort_coords(pnts):
        
        """
        Sort coordinates that make up a line.
        """
        
        # Run KNN
        nbrs = NearestNeighbors(n_neighbors=3, algorithm='kd_tree').fit(pnts)
        indices = nbrs.kneighbors(pnts, return_distance=False)
        
        # Init sorted list of indices
        sorted_idx = indices[0, [1, 0, 2]].tolist()
        
        # Add points right
        toggle = True
        while toggle:
            
            i = sorted_idx[-1]
            new_idx = indices[i, 1:]
            if new_idx[0] not in sorted_idx:
                
                next_i = new_idx[0]
            
            elif new_idx[1] not in sorted_idx:
                
                next_i = new_idx[1]
                
            else:
                
                toggle = False
                continue
            
            sorted_idx.append(next_i)
        
        # Invert sorted_idx
        sorted_idx = sorted_idx[::-1]
        
        # Add points left
        toggle = True
        while toggle:
            
            i = sorted_idx[-1]
            new_idx = indices[i, 1:]
            if new_idx[0] not in sorted_idx:
                
                next_i = new_idx[0]
            
            elif new_idx[1] not in sorted_idx:
                
                next_i = new_idx[1]
                
            else:
                
                toggle = False
                continue
            
            sorted_idx.append(next_i)
        
        sorted_pnts = pnts[sorted_idx]
        
        return sorted_pnts

### ------------------MAIN------------------ ###

try:
    
    import numpy as np
    import pandas as pd
    
    from matplotlib import pyplot as plt
    from PIL import Image as img
    from scipy.ndimage import binary_fill_holes as fill
    from scipy.ndimage import gaussian_filter as gaussian
    from scipy.ndimage import label
    from scipy.ndimage import minimum_filter as minfil
    from scipy.ndimage import maximum_filter as maxfil
    from scipy.signal import correlate #Easier math than convolution
    from sklearn.neighbors import NearestNeighbors
    from sys import argv
    
except:
    
    print("One or more dependencies are not installed.\nAlso, make sure your terminal has been activated.")
    exit()

### Read CLI

if '--help' in argv or '-h' in argv:
    
    display_help()
    quit()

else:
    
    sample_name, movie_path, masking, vesicles_removal, remove_background, scale, measurements_spacing = parse_args()

### Processing

# Init class
analysis = malpighian_movie_processing(movie_path, masking, vesicles_removal, remove_background, scale, measurements_spacing, sample_name)

# Process movie
analysis.process_movie()
