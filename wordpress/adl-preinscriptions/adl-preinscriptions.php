<?php
/**
 * Plugin Name: Pré-inscriptions Académie Delaveau
 * Description: Reçoit les candidatures du formulaire de pré-inscription, les range dans l'admin (menu « Pré-inscriptions », export CSV) et envoie un email à chaque nouvelle demande.
 * Version: 1.0.0
 * Requires at least: 6.0
 * Requires PHP: 7.4
 * Author: Académie Delaveau
 * License: GPL-2.0-or-later
 * Text Domain: adl-preinscriptions
 *
 * Source : dépôt GitHub du site, dossier wordpress/adl-preinscriptions.
 * Le formulaire de la page /pre-inscription-2027-2028/ envoie ses champs à POST /wp-json/adl/v1/preinscription.
 * Désactiver ou supprimer l'extension ne supprime aucune candidature.
 */

defined( 'ABSPATH' ) || exit;

final class ADL_Preinscriptions {

	const VERSION   = '1.0.0';
	const CPT       = 'adl_preinscription';
	const META      = 'adl_';
	const OPTION    = 'adl_preinscriptions_settings';
	const API_NS    = 'adl/v1';
	const HONEYPOT  = 'adl_site';
	const RATE      = 30; // candidatures enregistrées au maximum par heure et par adresse IP (plusieurs familles peuvent partager un wifi)

	/** Champs reçus : nom => [libellé, type, longueur maximale]. */
	public static function fields() {
		return array(
			'formation'           => array( 'Parcours', 'choice', 20 ),
			'prenom'              => array( 'Prénom', 'text', 100 ),
			'nom'                 => array( 'Nom', 'text', 100 ),
			'date_naissance'      => array( 'Date de naissance', 'date', 10 ),
			'niveau_actuel'       => array( 'Niveau scolaire / situation', 'text', 100 ),
			'adresse'             => array( 'Adresse', 'text', 300 ),
			'email'               => array( 'Email', 'email', 200 ),
			'telephone'           => array( 'Téléphone', 'text', 50 ),
			'responsable_nom'     => array( 'Responsable légal : nom', 'text', 200 ),
			'responsable_tel'     => array( 'Responsable légal : téléphone', 'text', 50 ),
			'responsable_email'   => array( 'Responsable légal : email', 'email', 200 ),
			'niveau_competition'  => array( 'Niveau de compétition', 'text', 100 ),
			'niveau_galop'        => array( 'Niveau Galop', 'text', 50 ),
			'cheval_propre'       => array( 'A un cheval', 'text', 50 ),
			'chevaux'             => array( 'Chevaux', 'textarea', 5000 ),
			'meilleurs_resultats' => array( 'Meilleurs résultats', 'textarea', 5000 ),
			'experience_equestre' => array( 'Expérience équestre', 'textarea', 5000 ),
			'disponibilites'      => array( 'Disponibilités', 'textarea', 5000 ),
			'club_actuel'         => array( 'Club / structure actuelle', 'text', 200 ),
			'objectifs'           => array( 'Objectifs sportifs', 'textarea', 5000 ),
			'motivations'         => array( 'Motivations', 'textarea', 5000 ),
			'lien_video'          => array( 'Lien des vidéos', 'url', 1000 ),
			'newsletter'          => array( 'Newsletter', 'bool', 3 ),
			'rgpd'                => array( 'Accord traitement des données', 'bool', 3 ),
		);
	}

	public static function parcours() {
		return array( 'Élite', 'Espoir', 'Le Lab' );
	}

	/** Droits : seuls les administrateurs et les éditeurs voient les candidatures. */
	public static function caps() {
		return array(
			'edit_adl_preinscriptions',
			'edit_others_adl_preinscriptions',
			'edit_private_adl_preinscriptions',
			'edit_published_adl_preinscriptions',
			'read_private_adl_preinscriptions',
			'delete_adl_preinscriptions',
			'delete_others_adl_preinscriptions',
			'delete_private_adl_preinscriptions',
			'delete_published_adl_preinscriptions',
			'publish_adl_preinscriptions',
		);
	}

	public static function boot() {
		add_action( 'init', array( __CLASS__, 'register_type' ) );
		add_action( 'rest_api_init', array( __CLASS__, 'register_route' ) );
		add_action( 'admin_init', array( __CLASS__, 'upgrade' ) );
		add_action( 'admin_init', array( __CLASS__, 'register_settings' ) );
		add_action( 'admin_menu', array( __CLASS__, 'admin_menu' ) );
		add_action( 'add_meta_boxes_' . self::CPT, array( __CLASS__, 'meta_boxes' ) );
		add_filter( 'manage_' . self::CPT . '_posts_columns', array( __CLASS__, 'columns' ) );
		add_action( 'manage_' . self::CPT . '_posts_custom_column', array( __CLASS__, 'column' ), 10, 2 );
		add_filter( 'manage_edit-' . self::CPT . '_sortable_columns', array( __CLASS__, 'sortable' ) );
		add_filter( 'post_row_actions', array( __CLASS__, 'row_actions' ), 10, 2 );
		add_action( 'restrict_manage_posts', array( __CLASS__, 'filters' ) );
		add_action( 'pre_get_posts', array( __CLASS__, 'filter_query' ) );
		add_action( 'manage_posts_extra_tablenav', array( __CLASS__, 'export_button' ) );
		add_action( 'admin_post_adl_preinscriptions_export', array( __CLASS__, 'export' ) );
		add_filter( 'private_title_format', array( __CLASS__, 'plain_title' ), 10, 2 );
		add_filter( 'display_post_states', array( __CLASS__, 'post_states' ), 10, 2 );
	}

	/* ------------------------------------------------------------------ Installation */

	public static function activate() {
		self::register_type();
		self::upgrade();
		$settings = get_option( self::OPTION );
		if ( ! is_array( $settings ) || empty( $settings['recipients'] ) ) {
			update_option( self::OPTION, array( 'recipients' => self::recipients_from_cf7() ) );
		}
	}

	public static function upgrade() {
		if ( get_option( 'adl_preinscriptions_version' ) === self::VERSION ) {
			return;
		}
		foreach ( array( 'administrator', 'editor' ) as $role_name ) {
			$role = get_role( $role_name );
			if ( $role ) {
				foreach ( self::caps() as $cap ) {
					$role->add_cap( $cap );
				}
			}
		}
		update_option( 'adl_preinscriptions_version', self::VERSION );
	}

	/** Reprend les destinataires du formulaire Contact Form 7 de pré-inscription, s'il existe. */
	private static function recipients_from_cf7() {
		$found = get_posts(
			array(
				'post_type'      => 'wpcf7_contact_form',
				'title'          => 'Pré-inscription 2027-2028',
				'posts_per_page' => 1,
				'post_status'    => 'any',
				'fields'         => 'ids',
			)
		);
		if ( $found ) {
			$mail = get_post_meta( $found[0], '_mail', true );
			if ( is_array( $mail ) && ! empty( $mail['recipient'] ) ) {
				$emails = self::parse_emails( $mail['recipient'] );
				if ( $emails ) {
					return implode( ', ', $emails );
				}
			}
		}
		return (string) get_option( 'admin_email' );
	}

	private static function parse_emails( $list ) {
		$emails = array();
		foreach ( preg_split( '/[,;\s]+/', (string) $list ) as $item ) {
			if ( preg_match( '/<([^>]+)>/', $item, $m ) ) {
				$item = $m[1];
			}
			$item = sanitize_email( $item );
			if ( $item && is_email( $item ) ) {
				$emails[] = $item;
			}
		}
		return array_values( array_unique( $emails ) );
	}

	public static function register_type() {
		register_post_type(
			self::CPT,
			array(
				'labels'              => array(
					'name'               => 'Pré-inscriptions',
					'singular_name'      => 'Pré-inscription',
					'menu_name'          => 'Pré-inscriptions',
					'all_items'          => 'Toutes les candidatures',
					'edit_item'          => 'Candidature',
					'view_item'          => 'Voir la candidature',
					'search_items'       => 'Rechercher un candidat',
					'not_found'          => 'Aucune candidature pour l’instant.',
					'not_found_in_trash' => 'Aucune candidature dans la corbeille.',
				),
				'public'              => false,
				'publicly_queryable'  => false,
				'exclude_from_search' => true,
				'show_ui'             => true,
				'show_in_menu'        => true,
				'show_in_nav_menus'   => false,
				'show_in_admin_bar'   => false,
				'show_in_rest'        => false,
				'menu_position'       => 26,
				'menu_icon'           => 'dashicons-id-alt',
				'supports'            => false,
				'has_archive'         => false,
				'rewrite'             => false,
				'query_var'           => false,
				'capability_type'     => array( 'adl_preinscription', 'adl_preinscriptions' ),
				'capabilities'        => array( 'create_posts' => 'do_not_allow' ),
				'map_meta_cap'        => true,
			)
		);
	}

	/* ------------------------------------------------------------------ Réception */

	public static function register_route() {
		register_rest_route(
			self::API_NS,
			'/preinscription',
			array(
				'methods'             => 'POST',
				'callback'            => array( __CLASS__, 'receive' ),
				'permission_callback' => '__return_true', // formulaire public : protégé par le piège à robots, la limite d'envois et reCAPTCHA
			)
		);
	}

	private static function clean( $type, $value, $max ) {
		if ( is_array( $value ) || is_object( $value ) ) {
			return '';
		}
		$value = trim( (string) $value );
		switch ( $type ) {
			case 'textarea':
				$value = sanitize_textarea_field( $value );
				break;
			case 'email':
				// Adresse refusée plutôt que « nettoyée » : sanitize_email retirerait les accents sans prévenir.
				$value = is_email( $value ) ? $value : '';
				break;
			case 'url':
				$value = esc_url_raw( $value, array( 'http', 'https' ) );
				break;
			case 'bool':
				return ( '' === $value || '0' === $value || 'false' === strtolower( $value ) ) ? '' : 'Oui';
			default:
				$value = sanitize_text_field( $value );
		}
		return mb_substr( $value, 0, $max );
	}

	public static function receive( WP_REST_Request $request ) {
		$ip      = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : '';
		$ip_key  = 'adl_pi_' . md5( $ip . wp_salt( 'nonce' ) );
		$attempt = (int) get_transient( $ip_key );
		if ( $attempt >= self::RATE ) {
			return new WP_Error( 'adl_rate_limited', 'Trop d’envois depuis cette connexion. Réessayez dans une heure.', array( 'status' => 429 ) );
		}

		$data   = array();
		$errors = array();
		foreach ( self::fields() as $name => $field ) {
			$raw            = $request->get_param( $name );
			$data[ $name ] = self::clean( $field[1], null === $raw ? '' : $raw, $field[2] );
			if ( null !== $raw && '' !== trim( (string) ( is_scalar( $raw ) ? $raw : '' ) ) && '' === $data[ $name ] && 'bool' !== $field[1] ) {
				$errors[ $name ] = 'valeur non valide';
			}
		}

		// Contrôles de base côté serveur (la page vérifie déjà chaque étape en détail).
		if ( ! in_array( $data['formation'], self::parcours(), true ) ) {
			$errors['formation'] = 'parcours inconnu';
		}
		foreach ( array( 'prenom', 'nom' ) as $name ) {
			if ( '' === $data[ $name ] ) {
				$errors[ $name ] = 'à renseigner';
			}
		}
		foreach ( array( 'email', 'responsable_email' ) as $name ) {
			if ( '' !== $data[ $name ] && ! is_email( $data[ $name ] ) ) {
				$errors[ $name ] = 'adresse non valide';
			}
		}
		if ( '' === $data['email'] && ! isset( $errors['email'] ) ) {
			$errors['email'] = 'à renseigner';
		}
		if ( '' !== $data['date_naissance'] && ( ! preg_match( '/^(\d{4})-(\d{2})-(\d{2})$/', $data['date_naissance'], $d ) || ! checkdate( (int) $d[2], (int) $d[3], (int) $d[1] ) ) ) {
			$errors['date_naissance'] = 'date non valide';
		}
		if ( '' === $data['rgpd'] ) {
			$errors['rgpd'] = 'accord nécessaire';
		}
		if ( $errors ) {
			return new WP_Error( 'adl_invalid', 'Certains champs sont à corriger.', array( 'status' => 400, 'errors' => $errors ) );
		}

		// Anti-spam : rien n'est rejeté, une demande douteuse est seulement marquée « à vérifier ».
		$suspect = '';
		$score   = '';
		if ( '' !== trim( (string) $request->get_param( self::HONEYPOT ) ) ) {
			$suspect = 'piège à robots rempli';
		} else {
			$check = self::recaptcha( (string) $request->get_param( 'recaptcha' ), $ip );
			$score = $check['score'];
			if ( $check['suspect'] ) {
				$suspect = $check['suspect'];
			}
		}

		set_transient( $ip_key, $attempt + 1, HOUR_IN_SECONDS ); // seules les candidatures enregistrées comptent

		$post_id = wp_insert_post(
			array(
				'post_type'   => self::CPT,
				'post_status' => 'private',
				'post_title'  => $data['formation'] . ' – ' . $data['prenom'] . ' ' . $data['nom'],
				'post_author' => 0,
			),
			true
		);
		if ( is_wp_error( $post_id ) || ! $post_id ) {
			return new WP_Error( 'adl_save_failed', 'La candidature n’a pas pu être enregistrée.', array( 'status' => 500 ) );
		}
		foreach ( $data as $name => $value ) {
			update_post_meta( $post_id, self::META . $name, $value );
		}
		update_post_meta( $post_id, '_adl_source', esc_url_raw( (string) $request->get_param( 'source' ) ) );
		update_post_meta( $post_id, '_adl_suspect', $suspect );
		update_post_meta( $post_id, '_adl_score', $score );

		if ( 'piège à robots rempli' !== $suspect ) {
			self::notify( $post_id, $data, $suspect );
		}
		return rest_ensure_response( array( 'ok' => true ) );
	}

	/** Vérifie le jeton reCAPTCHA v3 avec la clé secrète déjà enregistrée dans Contact Form 7, si elle existe. */
	private static function recaptcha( $token, $ip ) {
		$secret = '';
		$cf7    = get_option( 'wpcf7' );
		if ( is_array( $cf7 ) && ! empty( $cf7['recaptcha'] ) && is_array( $cf7['recaptcha'] ) ) {
			$secret = (string) reset( $cf7['recaptcha'] );
		}
		$secret = (string) apply_filters( 'adl_preinscriptions_recaptcha_secret', $secret );
		if ( '' === $secret ) {
			return array( 'score' => '', 'suspect' => '' );
		}
		if ( '' === $token ) {
			return array( 'score' => '', 'suspect' => 'pas de vérification anti-spam (reCAPTCHA bloqué ?)' );
		}
		$response = wp_remote_post(
			'https://www.google.com/recaptcha/api/siteverify',
			array(
				'timeout' => 8,
				'body'    => array( 'secret' => $secret, 'response' => $token, 'remoteip' => $ip ),
			)
		);
		if ( is_wp_error( $response ) ) {
			return array( 'score' => '', 'suspect' => '' ); // Google injoignable : on n'en tient pas rigueur au candidat.
		}
		$body = json_decode( wp_remote_retrieve_body( $response ), true );
		if ( empty( $body['success'] ) ) {
			return array( 'score' => '', 'suspect' => 'jeton anti-spam refusé' );
		}
		$score = isset( $body['score'] ) ? (float) $body['score'] : 1.0;
		return array( 'score' => (string) $score, 'suspect' => $score < 0.3 ? 'score anti-spam faible (' . $score . ')' : '' );
	}

	public static function recipients() {
		$settings = get_option( self::OPTION );
		$emails   = self::parse_emails( is_array( $settings ) && isset( $settings['recipients'] ) ? $settings['recipients'] : '' );
		return $emails ? $emails : array( (string) get_option( 'admin_email' ) );
	}

	private static function notify( $post_id, $data, $suspect ) {
		$lines = array( 'Nouvelle pré-inscription' . ( $suspect ? ' (à vérifier : ' . $suspect . ')' : '' ), '' );
		foreach ( self::fields() as $name => $field ) {
			if ( '' !== $data[ $name ] && 'rgpd' !== $name ) {
				$lines[] = $field[0] . ' : ' . $data[ $name ];
			}
		}
		$lines[] = '';
		$lines[] = 'Toutes les candidatures : ' . admin_url( 'edit.php?post_type=' . self::CPT );
		$lines[] = 'Cette candidature : ' . admin_url( 'post.php?post=' . $post_id . '&action=edit' );

		$subject = ( $suspect ? '[à vérifier] ' : '' ) . 'Pré-inscription : ' . $data['formation'] . ' - ' . $data['prenom'] . ' ' . $data['nom'];
		$headers = array( 'Content-Type: text/plain; charset=UTF-8' );
		if ( is_email( $data['email'] ) ) {
			$name      = trim( str_replace( array( '"', '<', '>' ), '', $data['prenom'] . ' ' . $data['nom'] ) );
			$headers[] = 'Reply-To: "' . $name . '" <' . $data['email'] . '>';
		}
		$sent = wp_mail( self::recipients(), $subject, implode( "\n", $lines ), $headers );
		update_post_meta( $post_id, '_adl_mail', $sent ? 'envoyé' : 'échec' );
	}

	/* ------------------------------------------------------------------ Admin : liste */

	public static function columns( $columns ) {
		return array(
			'cb'           => $columns['cb'],
			'title'        => 'Candidat',
			'adl_parcours' => 'Parcours',
			'adl_contact'  => 'Contact',
			'adl_age'      => 'Naissance',
			'adl_niveau'   => 'Niveau',
			'adl_recue'    => 'Reçue le',
		);
	}

	public static function sortable( $columns ) {
		$columns['adl_recue'] = 'date';
		return $columns;
	}

	public static function column( $column, $post_id ) {
		$get = function ( $name ) use ( $post_id ) {
			return (string) get_post_meta( $post_id, self::META . $name, true );
		};
		switch ( $column ) {
			case 'adl_parcours':
				echo esc_html( $get( 'formation' ) );
				$suspect = (string) get_post_meta( $post_id, '_adl_suspect', true );
				if ( $suspect ) {
					echo '<br><span style="color:#b32d2e" title="' . esc_attr( $suspect ) . '">À vérifier</span>';
				}
				break;
			case 'adl_contact':
				$email = $get( 'email' );
				$tel   = $get( 'telephone' );
				if ( $email ) {
					echo '<a href="' . esc_url( 'mailto:' . $email ) . '">' . esc_html( $email ) . '</a><br>';
				}
				if ( $tel ) {
					echo '<a href="' . esc_url( 'tel:' . preg_replace( '/[^0-9+]/', '', $tel ) ) . '">' . esc_html( $tel ) . '</a>';
				}
				break;
			case 'adl_age':
				echo esc_html( self::birth( $get( 'date_naissance' ) ) );
				break;
			case 'adl_niveau':
				echo esc_html( $get( 'niveau_actuel' ) );
				break;
			case 'adl_recue':
				echo esc_html( get_the_date( 'd/m/Y à H:i', $post_id ) );
				break;
		}
	}

	private static function birth( $date ) {
		if ( ! preg_match( '/^(\d{4})-(\d{2})-(\d{2})$/', $date, $m ) ) {
			return $date;
		}
		$age = (int) date_diff( date_create( $date ), date_create( 'today' ) )->y;
		return $m[3] . '/' . $m[2] . '/' . $m[1] . ' (' . $age . ' ans)';
	}

	public static function row_actions( $actions, $post ) {
		if ( self::CPT === $post->post_type ) {
			unset( $actions['inline hide-if-no-js'], $actions['view'] );
			if ( isset( $actions['edit'] ) ) {
				$actions['edit'] = str_replace( '>Modifier<', '>Ouvrir<', $actions['edit'] );
			}
		}
		return $actions;
	}

	public static function plain_title( $format, $post ) {
		return ( $post && self::CPT === get_post_type( $post ) ) ? '%s' : $format;
	}

	public static function post_states( $states, $post ) {
		if ( self::CPT === $post->post_type ) {
			unset( $states['private'] );
		}
		return $states;
	}

	public static function filters( $post_type ) {
		if ( self::CPT !== $post_type ) {
			return;
		}
		$current = isset( $_GET['adl_parcours'] ) ? sanitize_text_field( wp_unslash( $_GET['adl_parcours'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification
		echo '<label class="screen-reader-text" for="adl_parcours">Parcours</label><select name="adl_parcours" id="adl_parcours"><option value="">Tous les parcours</option>';
		foreach ( self::parcours() as $p ) {
			echo '<option value="' . esc_attr( $p ) . '"' . selected( $current, $p, false ) . '>' . esc_html( $p ) . '</option>';
		}
		echo '</select>';
	}

	public static function filter_query( $query ) {
		if ( ! is_admin() || ! $query->is_main_query() || self::CPT !== $query->get( 'post_type' ) ) {
			return;
		}
		$parcours = isset( $_GET['adl_parcours'] ) ? sanitize_text_field( wp_unslash( $_GET['adl_parcours'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification
		if ( in_array( $parcours, self::parcours(), true ) ) {
			$query->set( 'meta_query', array( array( 'key' => self::META . 'formation', 'value' => $parcours ) ) );
		}
	}

	public static function export_button( $which ) {
		$screen = get_current_screen();
		if ( 'top' !== $which || ! $screen || 'edit-' . self::CPT !== $screen->id || ! current_user_can( 'edit_others_adl_preinscriptions' ) ) {
			return;
		}
		$args = array( 'action' => 'adl_preinscriptions_export' );
		if ( ! empty( $_GET['adl_parcours'] ) ) { // phpcs:ignore WordPress.Security.NonceVerification
			$args['adl_parcours'] = sanitize_text_field( wp_unslash( $_GET['adl_parcours'] ) ); // phpcs:ignore WordPress.Security.NonceVerification
		}
		$url = wp_nonce_url( add_query_arg( $args, admin_url( 'admin-post.php' ) ), 'adl_preinscriptions_export' );
		echo '<div class="alignleft actions"><a class="button" href="' . esc_url( $url ) . '">Exporter en CSV (Excel)</a></div>';
	}

	public static function export() {
		if ( ! current_user_can( 'edit_others_adl_preinscriptions' ) ) {
			wp_die( 'Accès refusé.', '', array( 'response' => 403 ) );
		}
		check_admin_referer( 'adl_preinscriptions_export' );
		$args = array(
			'post_type'      => self::CPT,
			'post_status'    => array( 'private', 'publish' ),
			'posts_per_page' => -1,
			'orderby'        => 'date',
			'order'          => 'DESC',
		);
		$parcours = isset( $_GET['adl_parcours'] ) ? sanitize_text_field( wp_unslash( $_GET['adl_parcours'] ) ) : '';
		if ( in_array( $parcours, self::parcours(), true ) ) {
			$args['meta_query'] = array( array( 'key' => self::META . 'formation', 'value' => $parcours ) ); // phpcs:ignore WordPress.DB.SlowDBQuery
		}
		$posts = get_posts( $args );

		nocache_headers();
		header( 'Content-Type: text/csv; charset=UTF-8' );
		header( 'Content-Disposition: attachment; filename="pre-inscriptions-' . gmdate( 'Y-m-d' ) . '.csv"' );
		$out = fopen( 'php://output', 'w' );
		fwrite( $out, "\xEF\xBB\xBF" ); // pour qu'Excel lise les accents
		$header = array( 'Reçue le' );
		foreach ( self::fields() as $field ) {
			$header[] = $field[0];
		}
		$header[] = 'À vérifier';
		fputcsv( $out, $header, ';' );
		foreach ( $posts as $post ) {
			$row = array( get_the_date( 'd/m/Y H:i', $post ) );
			foreach ( array_keys( self::fields() ) as $name ) {
				$row[] = self::csv_cell( (string) get_post_meta( $post->ID, self::META . $name, true ) );
			}
			$row[] = self::csv_cell( (string) get_post_meta( $post->ID, '_adl_suspect', true ) );
			fputcsv( $out, $row, ';' );
		}
		fclose( $out );
		exit;
	}

	/** Empêche Excel d'interpréter une réponse comme une formule. */
	private static function csv_cell( $value ) {
		return preg_match( '/^[=+\-@\t\r]/', $value ) ? "'" . $value : $value;
	}

	/* ------------------------------------------------------------------ Admin : fiche */

	public static function meta_boxes( $post ) {
		remove_meta_box( 'slugdiv', self::CPT, 'normal' );
		add_meta_box( 'adl_candidature', 'Candidature', array( __CLASS__, 'render_box' ), self::CPT, 'normal', 'high' );
	}

	public static function render_box( $post ) {
		echo '<table class="widefat striped" style="border:0"><tbody>';
		echo '<tr><th style="width:240px">Reçue le</th><td>' . esc_html( get_the_date( 'd/m/Y à H:i', $post ) ) . '</td></tr>';
		foreach ( self::fields() as $name => $field ) {
			$value = (string) get_post_meta( $post->ID, self::META . $name, true );
			if ( '' === $value ) {
				continue;
			}
			switch ( $field[1] ) {
				case 'email':
					$html = '<a href="' . esc_url( 'mailto:' . $value ) . '">' . esc_html( $value ) . '</a>';
					break;
				case 'url':
					$html = '<a href="' . esc_url( $value ) . '" target="_blank" rel="noopener noreferrer">' . esc_html( $value ) . '</a>';
					break;
				case 'date':
					$html = esc_html( self::birth( $value ) );
					break;
				case 'textarea':
					$html = nl2br( esc_html( $value ) );
					break;
				default:
					$html = esc_html( $value );
			}
			if ( in_array( $name, array( 'telephone', 'responsable_tel' ), true ) ) {
				$html = '<a href="' . esc_url( 'tel:' . preg_replace( '/[^0-9+]/', '', $value ) ) . '">' . esc_html( $value ) . '</a>';
			}
			echo '<tr><th>' . esc_html( $field[0] ) . '</th><td>' . $html . '</td></tr>'; // phpcs:ignore WordPress.Security.EscapeOutput -- construit ci-dessus avec esc_*
		}
		$suspect = (string) get_post_meta( $post->ID, '_adl_suspect', true );
		$mail    = (string) get_post_meta( $post->ID, '_adl_mail', true );
		echo '<tr><th>Contrôle anti-spam</th><td>' . ( $suspect ? '<strong style="color:#b32d2e">À vérifier : ' . esc_html( $suspect ) . '</strong>' : 'OK' ) . '</td></tr>';
		echo '<tr><th>Email de notification</th><td>' . esc_html( $mail ? $mail : 'non envoyé' ) . '</td></tr>';
		echo '</tbody></table>';
	}

	/* ------------------------------------------------------------------ Admin : réglages */

	public static function admin_menu() {
		add_submenu_page( 'edit.php?post_type=' . self::CPT, 'Réglages des pré-inscriptions', 'Réglages', 'manage_options', 'adl-preinscriptions-reglages', array( __CLASS__, 'settings_page' ) );
	}

	public static function register_settings() {
		register_setting(
			'adl_preinscriptions',
			self::OPTION,
			array(
				'type'              => 'array',
				'sanitize_callback' => function ( $value ) {
					$emails = self::parse_emails( is_array( $value ) && isset( $value['recipients'] ) ? $value['recipients'] : '' );
					return array( 'recipients' => implode( ', ', $emails ) );
				},
			)
		);
	}

	public static function settings_page() {
		if ( ! current_user_can( 'manage_options' ) ) {
			return;
		}
		$settings = get_option( self::OPTION );
		$value    = is_array( $settings ) && isset( $settings['recipients'] ) ? $settings['recipients'] : '';
		echo '<div class="wrap"><h1>Réglages des pré-inscriptions</h1><form method="post" action="options.php">';
		settings_fields( 'adl_preinscriptions' );
		echo '<table class="form-table" role="presentation"><tr><th scope="row"><label for="adl_recipients">Emails prévenus à chaque candidature</label></th><td>';
		echo '<input type="text" class="regular-text" id="adl_recipients" name="' . esc_attr( self::OPTION ) . '[recipients]" value="' . esc_attr( $value ) . '">';
		echo '<p class="description">Plusieurs adresses séparées par des virgules. Vide : l’adresse d’administration du site.</p></td></tr></table>';
		submit_button();
		echo '</form></div>';
	}
}

ADL_Preinscriptions::boot();
register_activation_hook( __FILE__, array( 'ADL_Preinscriptions', 'activate' ) );
